"""Verify that every claim's verbatim_span is an exact substring of its source text.

The whole provenance story rests on one property: a `verbatim_span` is a literal quote, so any
reader can find it in the source and check that the claim was not paraphrased into something
stronger. Nothing in the extraction pipeline enforces that — the span is whatever the model
returned. This tool closes that gap: it re-reads the fetched source texts and confirms each span
is actually present, reporting the match rate per source and listing the misses.

It is deliberately forgiving about *formatting* noise that carries no meaning — whitespace runs,
smart vs. straight quotes, en/em dashes — because the fetched text and the model's copy often
differ only there, and flagging those would bury the failures that matter (a span that was
silently reworded). A span that matches only after that normalisation is reported as "normalized",
not "exact", so the distinction stays visible.

    python -m src.verify_spans --case blackholes
    python -m src.verify_spans --case covid --list-misses

Exit code is non-zero if any span fails even normalised matching, so this can gate a run.
"""

import argparse
import io
import os
import re
import sys
import unicodedata

# The fetcher prepends a "# ..." provenance header block; ingestion strips it before extraction,
# so spans are drawn from the body only. Mirror that here or leading-header text yields false misses.
_HEADER = re.compile(r"\A(?:#[^\n]*\n|\s*\n)+")


def _strip_header(text):
    return _HEADER.sub("", text, count=1)


def _normalize(s):
    """Collapse formatting-only differences that carry no propositional content."""
    s = unicodedata.normalize("NFKC", s)
    # unify quote and dash variants the fetcher and model disagree on
    s = (s.replace("‘", "'").replace("’", "'")
           .replace("“", '"').replace("”", '"')
           .replace("–", "-").replace("—", "-").replace("−", "-"))
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def _load_sources(raw_dir):
    """Read the fetched source bodies. Returns {} when they are absent.

    The raw texts are third-party articles (phys.org, ACX, Rootclaim, 4gravitons, ...) which we
    deliberately do not redistribute, so a fresh clone has no `raw/`. That is an expected state,
    not an error: the caller explains how to fetch them rather than dying on a traceback."""
    if not os.path.isdir(raw_dir):
        return {}
    bodies = {}
    for fn in sorted(os.listdir(raw_dir)):
        if not fn.endswith(".txt") or fn == "README.txt":
            continue
        with io.open(os.path.join(raw_dir, fn), encoding="utf-8", errors="replace") as fh:
            bodies[fn[:-4]] = _strip_header(fh.read())
    return bodies


def verify(case, root="."):
    base = os.path.join(root, "cases", case)
    with io.open(os.path.join(base, "out", "claims.json"), encoding="utf-8") as fh:
        import json
        claims = json.load(fh)["claims"]

    sources = _load_sources(os.path.join(base, "raw"))
    norm_sources = dict((sid, _normalize(body)) for sid, body in sources.items())

    stats = {}  # sid -> [exact, normalized, miss, total]
    misses = []
    for c in claims:
        for att in c.get("attestations", []):
            sid = att.get("source_id")
            span = att.get("verbatim_span", "") or ""
            st = stats.setdefault(sid, [0, 0, 0, 0])
            st[3] += 1
            if not span:
                st[2] += 1
                misses.append((c["id"], sid, "(empty span)"))
                continue
            if sid in sources and span in sources[sid]:
                st[0] += 1
            elif sid in norm_sources and _normalize(span) in norm_sources[sid]:
                st[1] += 1
            else:
                st[2] += 1
                misses.append((c["id"], sid, span[:80]))
    return stats, misses, set(sources)


_NO_RAW = """  span verification for case=%(case)s

  The raw source texts are NOT in this repository. They are third-party articles
  (phys.org, Astral Codex Ten, Rootclaim, 4gravitons, ...) and we do not redistribute
  copyrighted full text. This is expected on a fresh clone, not a failure.

  To reproduce this check yourself:
      python -m src.fetch --case %(case)s          # downloads them from cases/%(case)s/sources.json
      python -m src.verify_spans --case %(case)s

  The result of our own run is committed, so you can read the receipt without fetching:
      cases/%(case)s/out/span_verification.json
"""


def _write_report(path, case, stats, misses, known):
    """Persist the verification result so the receipt ships even when the sources cannot."""
    import json
    tot = [0, 0, 0, 0]
    per = {}
    for sid in sorted(stats):
        ex, nm, ms, t = stats[sid]
        for i, v in enumerate((ex, nm, ms, t)):
            tot[i] += v
        per[sid] = {"exact": ex, "normalized": nm, "miss": ms, "total": t}
    ex, nm, ms, t = tot
    t = t or 1
    report = {
        "case": case,
        "note": ("Every claim's verbatim_span re-checked against the fetched source text. "
                 "'exact' = literal substring; 'normalized' = matches after collapsing "
                 "formatting-only differences (smart quotes, dashes, whitespace); "
                 "'miss' = not found, i.e. the span was reworded and should not be trusted "
                 "as a quote. Raw sources are third-party and not redistributed; run "
                 "`python -m src.fetch --case %s` to regenerate them and re-run this check." % case),
        "sources_checked": sorted(known),
        "per_source": per,
        "totals": {"exact": ex, "normalized": nm, "miss": ms, "attestations": t},
        "percent_exact": round(100.0 * ex / t, 1),
        "percent_verified": round(100.0 * (ex + nm) / t, 1),
        "misses": [{"claim_id": c, "source_id": s, "span_prefix": sn} for c, s, sn in misses],
    }
    with io.open(path, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(report, indent=2, ensure_ascii=False))
    return report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", required=True)
    ap.add_argument("--root", default=".")
    ap.add_argument("--list-misses", action="store_true")
    ap.add_argument("--report", nargs="?", const="", default=None,
                    help="write the receipt to cases/<case>/out/span_verification.json (or a given path)")
    args = ap.parse_args()

    stats, misses, known = verify(args.case, args.root)

    if not known:
        # No source texts on disk: explain how to get them instead of reporting a bogus 0%.
        sys.stdout.write(_NO_RAW % {"case": args.case})
        sys.exit(2)

    if args.report is not None:
        path = args.report or os.path.join(
            args.root, "cases", args.case, "out", "span_verification.json")
        _write_report(path, args.case, stats, misses, known)
        print("  receipt written -> %s" % path)

    tot = [0, 0, 0, 0]
    print("  span verification for case=%s" % args.case)
    for sid in sorted(stats):
        ex, nm, ms, t = stats[sid]
        for i, v in enumerate((ex, nm, ms, t)):
            tot[i] += v
        flag = "" if sid in known else "  [NO RAW TEXT for this source]"
        print("    %-32s exact %3d  normalized %2d  miss %2d  of %3d%s"
              % (sid, ex, nm, ms, t, flag))
    ex, nm, ms, t = tot
    t = t or 1
    print("  -> %d/%d exact (%.1f%%), +%d normalized, %d miss  = %.1f%% verified"
          % (ex, t, 100.0 * ex / t, nm, ms, 100.0 * (ex + nm) / t))

    if args.list_misses and misses:
        print("\n  misses:")
        for cid, sid, snippet in misses[:60]:
            print("    %s [%s] %s" % (cid, sid, snippet))

    sys.exit(1 if ms else 0)


if __name__ == "__main__":
    main()
