"""Corpus-level independence: which underlying studies is a whole corpus leaning on?

The concentration layer (src/concentration.py) audits independence *inside* one debate's
claim graph. This module audits it *across documents*: when a corpus is an aggregate of many
briefs (e.g. another entrant's 40 evidence documents), how many of those "independent" briefs
actually rest on the *same underlying cited study*? Twenty briefs that all cite Pekar 2022 are,
on that point, one look — not twenty.

It is deterministic and content-agnostic: it extracts citation tokens (Author (YEAR) /
Author et al. YEAR, plus a few named documentary artifacts) from every claim's text + verbatim
spans, groups them by the source brief that asserts them, and reports how many DISTINCT briefs
invoke each underlying source. This is a coarser lens than the claim-graph Herfindahl — a
citation-string heuristic, not a resolved graph — and is labelled as such; its value is that it
catches the cross-document sharing that source-ordered edge windows miss.

    python -m src.source_independence --case carlo_audit
"""
import argparse
import json
import os
import re
from collections import defaultdict

# A citation is a first-author Surname sitting next to a (YEAR). We key on the SURNAME so a
# study's mentions aggregate ("Pekar 2022", "Pekar et al. (2022)", the 2024 erratum -> one root),
# which is the independence-relevant unit: how many briefs lean on Pekar's work at all.
_CITE = re.compile(
    r"\b([A-Z][a-zà-ÿ]{2,}(?:-[A-Z][a-zà-ÿ]+)?)"   # first-author surname (optional hyphen)
    r"(?:\s+et al\.?)?"                              # optional 'et al.'
    r"(?:\s*(?:,|and|&)\s*[A-Z][a-zà-ÿ]+)*"         # optional co-authors
    r"[\s,]*\(?((?:19|20)\d{2})[a-z]?\)?")          # the year (parens optional)
# tokens that look like "Surname YEAR" but are dates, journals, or places — not authors
_STOP = {"january", "february", "march", "april", "may", "june", "july", "august",
         "september", "october", "november", "december",
         "jan", "feb", "mar", "apr", "jun", "jul", "aug", "sep", "sept", "oct", "nov", "dec",
         "science", "nature", "cell", "evolution", "virology", "lancet", "bmj", "pnas",
         "biorxiv", "medrxiv", "arxiv", "bulletin", "report", "house", "senate", "spring",
         "summer", "winter", "autumn", "fall", "the", "this", "wuhan", "china", "beijing",
         "lineage", "figure", "table", "since", "between", "early", "late", "mid"}
# named documentary artifacts that are single sources but rarely carry a year in-line
_NAMED = {
    "DEFUSE proposal": r"defuse",
    "RaTG13 sequence": r"ratg13",
    "Proximal Origin": r"proximal origin",
}


def _citations(text):
    """Return the set of underlying-source keys (author surnames / named artifacts) cited here."""
    keys = set()
    for surname, _year in _CITE.findall(text):
        if surname.lower() in _STOP:
            continue
        keys.add(surname)
    low = text.lower()
    for label, pat in _NAMED.items():
        if re.search(pat, low):
            keys.add(label)
    return keys


def analyze(case, root="."):
    path = os.path.join(root, "cases", case, "out", "graph.json")
    with open(path, encoding="utf-8") as f:
        graph = json.load(f)

    # text asserted by each source brief
    by_brief = defaultdict(list)
    for c in graph["claims"]:
        for a in c.get("attestations", []):
            blob = " ".join([c.get("text", ""), a.get("verbatim_span", ""), a.get("context", "")])
            by_brief[a.get("source_id", "?")].append(blob)

    briefs = {s: _citations(" ".join(v)) for s, v in by_brief.items()}
    n_briefs = len(briefs)

    # how many DISTINCT briefs invoke each underlying source
    shared = defaultdict(set)
    for sid, cites in briefs.items():
        for k in cites:
            shared[k].add(sid)
    ranked = sorted(((k, sorted(v)) for k, v in shared.items() if len(v) >= 2),
                    key=lambda kv: -len(kv[1]))

    print(f"corpus: {n_briefs} briefs\n")
    print("underlying source            briefs  (an item shared by many briefs is one look, not many)")
    for key, sids in ranked[:20]:
        print(f"  {key:28s} {len(sids):3d}")
    out = {
        "case": case,
        "method": "shared-citation heuristic (Author-YEAR + named artifacts); coarse cross-document independence lens",
        "brief_count": n_briefs,
        "shared_sources": [{"source": k, "brief_count": len(s), "briefs": s} for k, s in ranked],
    }
    out_path = os.path.join(root, "cases", case, "out", "source_independence.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(f"\n  -> {out_path}")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", required=True)
    ap.add_argument("--root", default=".")
    args = ap.parse_args()
    analyze(args.case, args.root)


if __name__ == "__main__":
    main()
