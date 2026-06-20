"""Assessment stage: graph -> ranked cruxes (+ correlated-evidence flags).

Operates over the explicit structure built in the previous stage — this is the point of
'structure-before-assess'. Crux ranking is model-driven over the dependency edges, with a
deterministic graph-centrality fallback so the pipeline always produces *something*
defensible even if the model pass is weak.
"""
import json
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from prompts.structure_assess import CRUX_SYSTEM, CORRELATED_SYSTEM  # noqa: E402
from src.llm import call_json  # noqa: E402


def assess(case: str, root: str = ".") -> dict:
    case_dir = os.path.join(root, "cases", case)
    with open(os.path.join(case_dir, "out", "graph.json"), encoding="utf-8") as f:
        graph = json.load(f)

    payload = _payload(graph)

    print("  detecting cruxes (model-driven over dependency graph)...")
    try:
        cruxes = call_json(CRUX_SYSTEM, payload)
    except Exception as e:
        print(f"    [warn] model crux pass failed ({e}); using centrality fallback.")
        cruxes = _centrality_fallback(graph)

    print("  flagging correlated evidence (stretch)...")
    try:
        correlated = call_json(CORRELATED_SYSTEM, payload)
    except Exception as e:
        print(f"    [warn] correlated-evidence pass failed ({e}); skipping.")
        correlated = []

    graph["assessment"] = {"cruxes": cruxes, "correlated_evidence_flags": correlated}
    with open(os.path.join(case_dir, "out", "graph.json"), "w", encoding="utf-8") as f:
        json.dump(graph, f, indent=2, ensure_ascii=False)
    with open(os.path.join(case_dir, "out", "cruxes.json"), "w", encoding="utf-8") as f:
        json.dump(cruxes, f, indent=2, ensure_ascii=False)

    print(f"  -> {len(cruxes)} cruxes ranked; written to {case_dir}/out/cruxes.json")
    if cruxes:
        top = cruxes[0]
        print(f"  TOP CRUX: {top.get('claim_id')} (sensitivity {top.get('sensitivity')}) "
              f"-> {top.get('affects')}")
    return graph


def _payload(graph):
    claims = "\n".join(
        f'{c["id"]} [{c["kind"]}]: {c["text"]}'
        + (f'  | est: {c["probability_estimates"]}' if c.get("probability_estimates") else "")
        for c in graph["claims"]
    )
    edges = "\n".join(f'{e["from"]} --{e["type"]}({e.get("strength","")})--> {e["to"]}'
                      for e in graph["edges"])
    conclusions = [c["id"] + ": " + c["text"] for c in graph["claims"] if c["kind"] == "conclusion"]
    return (f"CONCLUSIONS:\n" + "\n".join(conclusions)
            + f"\n\nCLAIMS:\n{claims}\n\nEDGES:\n{edges}")


def _centrality_fallback(graph):
    """Deterministic fallback: a crux is a claim that OTHER claims/conclusions rest on.
    So we score by weighted OUT-degree on depends_on / is_evidence_for / supports edges
    (i.e. how much this claim props up), not in-degree. Always defensible and reproducible."""
    weight = {"depends_on": 1.0, "is_evidence_for": 0.7, "supports": 0.5}
    score = defaultdict(float)
    for e in graph["edges"]:
        # 'from' supports/grounds 'to' — so 'from' is the load-bearing node
        score[e["from"]] += weight.get(e["type"], 0.2)
    ranked = sorted(score.items(), key=lambda kv: kv[1], reverse=True)
    mx = ranked[0][1] if ranked else 1.0
    text = {c["id"]: c["text"] for c in graph["claims"]}
    return [
        {"claim_id": cid, "sensitivity": round(s / mx, 3),
         "affects": "conclusion (centrality estimate)",
         "rationale": f"High weighted out-degree ({s:.1f}) on dependency/evidence edges — "
                      f"other claims rest on '{text.get(cid,'')[:80]}'."}
        for cid, s in ranked[:10]
    ]
