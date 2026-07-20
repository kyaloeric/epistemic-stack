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


def verify(case, root="."):
    base = os.path.join(root, "cases", case)
    with io.open(os.path.join(base, "out", "claims.json"), encoding="utf-8") as fh:
        import json
        claims = json.load(fh)["claims"]

    raw_dir = os.path.join(base, "raw")
    sources, norm_sources = {}, {}
    for fn in os.listdir(raw_dir):
        if not fn.endswith(".txt") or fn == "README.txt":
            continue
        sid = fn[:-4]
        with io.open(os.path.join(raw_dir, fn), encoding="utf-8", errors="replace") as fh:
            body = _strip_header(fh.read())
        sources[sid] = body
        norm_sources[sid] = _normalize(body)

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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", required=True)
    ap.add_argument("--root", default=".")
    ap.add_argument("--list-misses", action="store_true")
    args = ap.parse_args()

    stats, misses, known = verify(args.case, args.root)
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
