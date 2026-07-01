"""Assessment stage: graph -> ranked cruxes (+ correlated-evidence flags).

Operates over the explicit structure built in the previous stage — this is the point of
'structure-before-assess'. DESIGN: the numbers are deterministic. Crux sensitivity is computed
by transparent graph arithmetic (src.concentration), and correlated/circular evidence is found
by SCC over the support graph. The LLM is demoted to an OPTIONAL narration pass that attaches a
human-readable dependency story to each crux — it can enrich the explanation but can never
change the ranking or the score. 'The graph proposes and computes; the model only narrates.'
This is what makes the headline result reproducible and auditable rather than 'the model said so'.
"""
import json
import math
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from prompts.structure_assess import CRUX_SYSTEM, CORRELATED_SYSTEM  # noqa: E402
from src.concentration import concentration_for, circular_support_flags  # noqa: E402
from src.llm import call_json, provider_info  # noqa: E402


def assess(case: str, root: str = ".") -> dict:
    case_dir = os.path.join(root, "cases", case)
    with open(os.path.join(case_dir, "out", "graph.json"), encoding="utf-8") as f:
        graph = json.load(f)

    # --- 1. DETERMINISTIC crux ranking (the number, computed from the graph) ---
    print("  ranking cruxes (deterministic graph concentration)...")
    cruxes = _deterministic_cruxes(graph)

    # --- 2. DETERMINISTIC correlated / circular evidence (SCC over support graph) ---
    print("  detecting correlated & circular evidence (deterministic SCC)...")
    correlated = circular_support_flags(graph)

    # --- 3. OPTIONAL model narration (enrichment only; never changes the numbers) ---
    print("  enriching with model narration (optional; numbers already fixed)...")
    _narrate(graph, cruxes, correlated)

    graph["assessment"] = {"cruxes": cruxes, "correlated_evidence_flags": correlated,
                           "method": "deterministic concentration + SCC; model narration only"}
    with open(os.path.join(case_dir, "out", "graph.json"), "w", encoding="utf-8") as f:
        json.dump(graph, f, indent=2, ensure_ascii=False)
    with open(os.path.join(case_dir, "out", "cruxes.json"), "w", encoding="utf-8") as f:
        json.dump(cruxes, f, indent=2, ensure_ascii=False)

    print(f"  -> {len(cruxes)} cruxes ranked; written to {case_dir}/out/cruxes.json")
    if cruxes:
        top = cruxes[0]
        print(f"  TOP CRUX: {top['claim_id']} (sensitivity {top['sensitivity']}) "
              f"-> {top['affects']}")
    if correlated:
        print(f"  [!] {len(correlated)} circular-support loop(s) flagged")
    return graph


# a conclusion resting on fewer than this many claims is an under-developed stub, not a real
# node with a crux — its lone supporters are trivially "100% load-bearing" and must not dominate.
MIN_CONCLUSION_SUPPORT = 3


def _deterministic_cruxes(graph):
    """A crux is a claim that carries a large share of a SUBSTANTIVELY supported conclusion.

    `sensitivity` = the largest support-share the claim holds over any qualifying conclusion
    (0-1): flip it and roughly that fraction of that conclusion's grounding goes with it. But
    share alone rewards stubs (a 1-supporter conclusion is trivially 100% concentrated), so we
    (1) skip conclusions below MIN_CONCLUSION_SUPPORT and (2) rank by `score = share *
    log2(1+supporters)` — carrying 23% of a 104-claim conclusion beats carrying 100% of a
    1-claim stub. Pure graph arithmetic, reproducible by re-running src.concentration."""
    conclusions = [c["id"] for c in graph["claims"] if c["kind"] == "conclusion"]
    conclusion_set = set(conclusions)
    best = {}  # claim_id -> crux dict
    for cid in conclusions:
        r = concentration_for(graph, cid)
        n_support = r.get("supporting_claim_count", len(r.get("contributions", [])))
        if n_support < MIN_CONCLUSION_SUPPORT:
            continue  # under-developed conclusion — no meaningful crux to surface
        weight = math.log2(1 + n_support)
        for contrib in r["contributions"]:
            claim_id, share = contrib["claim_id"], contrib["share"]
            if claim_id in conclusion_set:
                continue  # a conclusion is never a crux for another conclusion
            score = share * weight
            if claim_id not in best or score > best[claim_id]["score"]:
                best[claim_id] = {
                    "claim_id": claim_id,
                    "sensitivity": round(share, 3),
                    "score": round(score, 3),
                    "affects": r["conclusion_text"][:80] or cid,
                    "affects_id": cid,
                    "affects_support_count": n_support,
                    "rationale": (
                        f"Carries {int(share * 100)}% of the evidential support for conclusion "
                        f"{cid}, which is backed by {n_support} claims "
                        f"(~{r['effective_independent_claims']} effective independent). "
                        f"Ranked by share x log2(1+support) so stubs can't dominate."),
                    "method": "deterministic",
                }
    ranked = sorted(best.values(), key=lambda c: c["score"], reverse=True)
    return ranked[:10]


def _narrate(graph, cruxes, correlated):
    """Best-effort LLM enrichment. Attaches a `model_rationale` dependency story to cruxes and
    a `model_note` to circular flags. Wrapped so any failure leaves the deterministic output
    fully intact — the model is never in the critical path."""
    if not provider_info()[0]:
        print("    [info] no LLM key set; skipping narration (deterministic output stands).")
        return
    payload = _payload(graph)
    try:
        narration = call_json(CRUX_SYSTEM, payload)
        by_id = {n.get("claim_id"): n.get("rationale", "")
                 for n in narration if isinstance(n, dict)}
        for c in cruxes:
            if c["claim_id"] in by_id and by_id[c["claim_id"]]:
                c["model_rationale"] = by_id[c["claim_id"]]
    except Exception as e:
        print(f"    [warn] crux narration skipped ({e}); deterministic rationale retained.")
    if not correlated:
        return
    try:
        notes = call_json(CORRELATED_SYSTEM, payload)
        # attach any model-identified correlation notes as supplementary context
        if isinstance(notes, list) and notes:
            for f in correlated:
                f["model_notes"] = [n for n in notes if isinstance(n, dict)]
                break
    except Exception as e:
        print(f"    [warn] correlated-evidence narration skipped ({e}).")


def _payload(graph):
    claims = "\n".join(
        f'{c["id"]} [{c["kind"]}]: {c["text"]}'
        + (f'  | est: {c["probability_estimates"]}' if c.get("probability_estimates") else "")
        for c in graph["claims"]
    )
    edges = "\n".join(f'{e["from"]} --{e["type"]}({e.get("strength","")})--> {e["to"]}'
                      for e in graph["edges"])
    conclusions = [c["id"] + ": " + c["text"] for c in graph["claims"] if c["kind"] == "conclusion"]
    return ("CONCLUSIONS:\n" + "\n".join(conclusions)
            + f"\n\nCLAIMS:\n{claims}\n\nEDGES:\n{edges}")
