"""Cross-source edge pass driven by semantic candidate selection.

Same prompt, same parser, same normalisation as the in-pipeline edge stage — the only thing that
changes is *which claim pairs the model is asked about*. Windows come from `src.semantic`
(TF-IDF nearest neighbours, cross-source-weighted) instead of from position in the claim list,
which is what makes cross-source relations findable on a corpus of this size (PRIMARY §5).

Runs as a standalone stage over an existing graph so a case that has already paid for ingestion
and the within-source pass can gain cross-source structure without re-extracting anything.

    # emit prompts for a relay operator (no API key needed)
    EPISTEMIC_RELAY_DIR=relay/covid python -m src.semantic_edges --case covid
    # ...answer them into relay/covid/responses/, then re-run the identical command

With a normal provider key set it simply runs end to end.
"""

import argparse
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from prompts.structure_assess import EDGES_SYSTEM  # noqa: E402
from src import llm  # noqa: E402
from src.llm import call_json  # noqa: E402
from src.merge_edges import merge  # noqa: E402
from src.semantic import group_stats, semantic_groups  # noqa: E402
from src.structure import _as_list, _claims_brief, _normalize_edges  # noqa: E402

SEED_KINDS = ("conclusion", "inference")


def _source_of(claim):
    att = claim.get("attestations") or []
    return att[0]["source_id"] if att else "?"


def run(case, root=".", window=80, min_sim=0.05, dry_run=False):
    base = os.path.join(root, "cases", case)
    graph_path = os.path.join(base, "out", "graph.json")
    with io.open(graph_path, encoding="utf-8") as fh:
        graph = json.load(fh)
    with io.open(os.path.join(base, "sources.json"), encoding="utf-8") as fh:
        sides = {s["id"]: s.get("side") for s in json.load(fh)["sources"]}

    claims = graph["claims"]
    print("  selecting candidates semantically (deterministic, no model)...")
    groups = semantic_groups(
        claims, _source_of, window=window, min_sim=min_sim,
        seed_if=lambda c: c.get("kind") in SEED_KINDS,
    )
    stats = group_stats(groups, _source_of)
    print("  -> %d windows | mean %s claims | mean %s sources/window | %d single-source"
          % (stats["groups"], stats["mean_size"], stats["mean_sources"],
             stats["single_source_groups"]))

    print("  extracting edges over semantic windows...")
    raw, answered = [], 0
    for i, group in enumerate(groups):
        try:
            reply = call_json(EDGES_SYSTEM, _claims_brief(group))
        except Exception as e:
            print("    [warn] window %d failed (%s); skipping." % (i, e))
            continue
        found = _as_list(reply, ("edges", "relations", "relationships"))
        if found:
            answered += 1
        raw.extend(ed for ed in found if isinstance(ed, dict))

    print("  -> %d windows returned edges; %d raw edges before normalisation"
          % (answered, len(raw)))

    outstanding = llm.relay_report()
    if not raw:
        print("\n  no edges produced — nothing written.")
        return graph, {"added": 0}

    ids = {c["id"] for c in claims}
    clean = [e for e in _normalize_edges(
        [e for e in raw
         if e.get("from") in ids and e.get("to") in ids and e.get("from") != e.get("to")]
    )]
    for e in clean:
        e.setdefault("source_id", "cross_source")
        e["extraction"] = "semantic_window"
    print("  -> %d edges survive endpoint validation + reciprocal collapse" % len(clean))

    before = len(graph["edges"])
    graph, report = merge(graph, clean, sides)
    print("  -> merged: edges %d -> %d (+%d; %d duplicate of existing)"
          % (before, len(graph["edges"]), report["added"], report["duplicate"]))
    print("     of the new edges: %d cross-source, %d cross-side"
          % (report["cross_source"], report["cross_side"]))

    if dry_run or outstanding:
        if outstanding:
            print("\n  [dry] prompts still outstanding — graph.json NOT written. "
                  "Answer them and re-run to commit real output.")
        else:
            print("\n  [dry-run] graph.json not written")
        return graph, report

    with io.open(graph_path, "w", encoding="utf-8") as fh:
        json.dump(graph, fh, ensure_ascii=False, indent=2)
    print("\n  wrote %s" % graph_path)
    return graph, report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", required=True)
    ap.add_argument("--root", default=".")
    ap.add_argument("--window", type=int, default=80)
    ap.add_argument("--min-sim", type=float, default=0.05)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    provider, model = llm.provider_info()
    print("== semantic cross-source edge pass :: case=%s provider=%s model=%s =="
          % (args.case, provider, model))
    run(args.case, args.root, args.window, args.min_sim, args.dry_run)


if __name__ == "__main__":
    main()
