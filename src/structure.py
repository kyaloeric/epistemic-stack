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

    if not claims:
        print("  [skip] no claims to structure — ingestion produced 0 claims. "
              "Check the ingestion warnings above (e.g. extraction/chunking failures).")
        graph = {"case": case, "sources": data["sources"], "claims": [], "edges": []}
        with open(os.path.join(case_dir, "out", "graph.json"), "w", encoding="utf-8") as f:
            json.dump(graph, f, indent=2, ensure_ascii=False)
        return graph

    # --- dedup (windowed so large corpora never overflow a single call) ---
    print("  deduplicating claims across sources...")
    clusters = _dedup_windowed(claims)
    merged, alias = _apply_clusters(claims, clusters)
    print(f"  -> {len(claims)} claims merged to {len(merged)}")

    # --- edges (windowed: one call per overlapping batch, unioned) ---
    print("  extracting edges (inference + discourse structure)...")
    edges = _edges_windowed(merged)
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


def _dedup_windowed(claims, window=120, overlap=20):
    """Deduplicate in overlapping windows so a big corpus never overflows one call.
    Each claim lands in at most one cluster (a global `claimed` set enforces this), so the
    windows can safely overlap to catch restatements that straddle a boundary. Conservative by
    construction: cross-window duplicates that never co-occur in a window stay separate — which
    matches the 'only merge true restatements' stance."""
    if not claims:
        return []
    clusters, claimed = [], set()
    step = max(1, window - overlap)
    for start in range(0, len(claims), step):
        batch = claims[start:start + window]
        if not batch:
            break
        try:
            batch_clusters = call_json(DEDUP_SYSTEM, _claims_brief(batch))
        except Exception as e:
            print(f"    [warn] dedup batch at {start} failed ({e}); leaving those claims distinct.")
            batch_clusters = []
        for cl in batch_clusters if isinstance(batch_clusters, list) else []:
            mids = [m for m in cl.get("member_ids", []) if m not in claimed]
            if len(mids) >= 2:
                clusters.append({"canonical_text": cl.get("canonical_text", ""), "member_ids": mids})
                claimed.update(mids)
        if start + window >= len(claims):
            break
    return clusters


def _edges_windowed(merged, window=60, overlap=15):
    """Extract edges in overlapping windows and union them. Output size (not input) is what
    truncates the model, so we cap how many claims each call must relate. Overlap catches edges
    near window boundaries. Long-range edges between very distant claims can be missed — a known
    trade for scalability; most inference/discourse edges are local to a reasoning neighborhood."""
    edges, seen = [], set()
    step = max(1, window - overlap)
    for start in range(0, len(merged), step):
        batch = merged[start:start + window]
        if not batch:
            break
        try:
            batch_edges = call_json(EDGES_SYSTEM, _claims_brief(batch))
        except Exception as e:
            print(f"    [warn] edge batch at {start} failed ({e}); skipping that batch.")
            batch_edges = []
        for ed in batch_edges if isinstance(batch_edges, list) else []:
            frm, to, typ = ed.get("from"), ed.get("to"), ed.get("type")
            if not frm or not to:
                continue
            key = (frm, to, typ)
            if key not in seen:
                seen.add(key)
                edges.append(ed)
        if start + window >= len(merged):
            break
    return edges


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
