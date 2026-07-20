"""Merge an externally-produced edge set into an existing claim graph.

Additive by construction: existing edges are never dropped. Every incoming edge is
validated against the claims already in the graph, so a merge cannot invent nodes.
Duplicates (same from/to/type) are skipped rather than stacked, which keeps the
concentration and Herfindahl maths honest — a claim cannot be inflated by re-import.

Usage:
    python -m src.merge_edges --case covid --edges cases/covid/manual_edges.json
    python -m src.merge_edges --case covid --edges ... --dry-run
"""

import argparse
import io
import json
import os

VALID_TYPES = {
    "supports", "contradicts", "is_evidence_for",
    "restates", "caveats", "depends_on", "context_mutation",
}


def _load(path):
    with io.open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _dump(path, obj):
    with io.open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=2)


def _first_source(claim):
    att = claim.get("attestations") or []
    return att[0]["source_id"] if att else None


def merge(graph, incoming, sides=None):
    """Return (merged_graph, report). Pure — does not touch disk."""
    by_id = {c["id"]: c for c in graph["claims"]}
    sides = sides or {}
    seen = {(e["from"], e["to"], e["type"]) for e in graph["edges"]}

    added, report = [], {
        "submitted": len(incoming), "added": 0, "duplicate": 0,
        "unknown_claim": [], "bad_type": [], "self_edge": 0,
        "cross_source": 0, "cross_side": 0,
    }

    for e in incoming:
        f, t, typ = e.get("from"), e.get("to"), e.get("type")
        if typ not in VALID_TYPES:
            report["bad_type"].append("%s->%s:%s" % (f, t, typ))
            continue
        if f not in by_id or t not in by_id:
            report["unknown_claim"].append("%s->%s" % (f, t))
            continue
        if f == t:
            report["self_edge"] += 1
            continue
        if (f, t, typ) in seen:
            report["duplicate"] += 1
            continue
        seen.add((f, t, typ))
        added.append(e)
        sf, st = _first_source(by_id[f]), _first_source(by_id[t])
        if sf != st:
            report["cross_source"] += 1
            if sides.get(sf) != sides.get(st):
                report["cross_side"] += 1

    report["added"] = len(added)
    graph["edges"] = graph["edges"] + added
    return graph, report


def _tally(graph, sides):
    by_id = {c["id"]: c for c in graph["claims"]}
    xs = xd = 0
    for e in graph["edges"]:
        f, t = by_id.get(e["from"]), by_id.get(e["to"])
        if not f or not t:
            continue
        sf, st = _first_source(f), _first_source(t)
        if sf != st:
            xs += 1
            if sides.get(sf) != sides.get(st):
                xd += 1
    return xs, xd


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", required=True)
    ap.add_argument("--edges", required=True)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    base = os.path.join("cases", args.case)
    graph_path = os.path.join(base, "out", "graph.json")
    graph = _load(graph_path)
    sides = {s["id"]: s.get("side") for s in _load(os.path.join(base, "sources.json"))["sources"]}

    payload = _load(args.edges)
    incoming = payload["edges"] if isinstance(payload, dict) else payload

    before = len(graph["edges"])
    xs0, xd0 = _tally(graph, sides)
    graph, report = merge(graph, incoming, sides)
    xs1, xd1 = _tally(graph, sides)

    print("edges        %d -> %d  (+%d of %d submitted)"
          % (before, len(graph["edges"]), report["added"], report["submitted"]))
    print("cross-source %d -> %d" % (xs0, xs1))
    print("cross-side   %d -> %d" % (xd0, xd1))
    print("skipped      duplicate=%d self=%d unknown=%d bad_type=%d"
          % (report["duplicate"], report["self_edge"],
             len(report["unknown_claim"]), len(report["bad_type"])))
    for label in ("unknown_claim", "bad_type"):
        if report[label]:
            print("  %s: %s" % (label, ", ".join(report[label][:20])))

    if args.dry_run:
        print("\n[dry-run] graph.json not written")
        return
    _dump(graph_path, graph)
    print("\nwrote %s" % graph_path)


if __name__ == "__main__":
    main()
