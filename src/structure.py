"""Structure stage: claims -> deduplicated typed claim graph.

1. Merge cross-source restatements (conservative — keeps 'similar-but-not-identical' distinct).
2. Extract typed edges (supports/contradicts/depends_on/...).
Writes cases/<case>/out/graph.json.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from prompts.structure_assess import DEDUP_SYSTEM, EDGES_SYSTEM  # noqa: E402
from src.llm import call_json  # noqa: E402


def _claims_brief(claims):
    """Compact id+text+side listing to fit the model context."""
    lines = []
    for c in claims:
        side = c["attestations"][0]["source_id"] if c["attestations"] else "?"
        lines.append(f'{c["id"]} [{c["kind"]}] ({side}): {c["text"]}')
    return "\n".join(lines)


def structure(case: str, root: str = ".") -> dict:
    case_dir = os.path.join(root, "cases", case)
    with open(os.path.join(case_dir, "out", "claims.json"), encoding="utf-8") as f:
        data = json.load(f)
    claims = data["claims"]

    # --- dedup ---
    print("  deduplicating claims across sources...")
    clusters = call_json(DEDUP_SYSTEM, _claims_brief(claims))
    merged, alias = _apply_clusters(claims, clusters)
    print(f"  -> {len(claims)} claims merged to {len(merged)}")

    # --- edges ---
    print("  extracting edges (inference + discourse structure)...")
    edges = call_json(EDGES_SYSTEM, _claims_brief(merged))
    # remap any edge endpoints that pointed at merged-away ids
    for e in edges:
        e["from"] = alias.get(e["from"], e["from"])
        e["to"] = alias.get(e["to"], e["to"])
    print(f"  -> {len(edges)} edges")

    graph = {"case": case, "sources": data["sources"], "claims": merged, "edges": edges}
    with open(os.path.join(case_dir, "out", "graph.json"), "w", encoding="utf-8") as f:
        json.dump(graph, f, indent=2, ensure_ascii=False)
    print(f"  -> graph written to {case_dir}/out/graph.json")
    return graph


def _apply_clusters(claims, clusters):
    """Merge member claims into a canonical claim; return (merged_claims, alias_map)."""
    by_id = {c["id"]: c for c in claims}
    alias = {}
    merged_ids = set()
    merged = []
    for cl in clusters:
        members = [by_id[mid] for mid in cl["member_ids"] if mid in by_id]
        if not members:
            continue
        canonical = members[0]
        canonical["text"] = cl.get("canonical_text", canonical["text"])
        for m in members[1:]:
            canonical["attestations"].extend(m["attestations"])
            canonical["probability_estimates"].extend(m.get("probability_estimates", []))
            alias[m["id"]] = canonical["id"]
            merged_ids.add(m["id"])
        merged.append(canonical)
        merged_ids.add(canonical["id"])
    # add untouched claims
    for c in claims:
        if c["id"] not in merged_ids:
            merged.append(c)
    return merged, alias
