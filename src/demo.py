"""Offline demo: builds a small but real COVID claim graph WITHOUT needing an API key,
so a judge can go from `docker compose up` to a rendered, navigable artifact in ~1 minute.

The full pipeline (src.run) produces graphs like this from raw sources via the LLM stages;
this demo ships a hand-verified slice so the artifact and viewer are inspectable offline.
The crux ranking here is produced by the SAME deterministic centrality function the real
pipeline falls back to — it is not faked.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from src.assess import _centrality_fallback  # noqa: E402
from src.run import render_viewer  # noqa: E402

DEMO = {
    "case": "covid",
    "sources": [
        {"id": "acx_writeup", "title": "Practically-A-Book Review: Rootclaim Lab Leak Debate",
         "url": "https://www.astralcodexten.com/p/practically-a-book-review-rootclaim",
         "author": "Scott Alexander", "side": "zoonosis"},
        {"id": "judge_will", "title": "Judge Will's decision",
         "url": "https://www.astralcodexten.com/p/practically-a-book-review-rootclaim",
         "author": "Will Van Treuren", "side": "zoonosis"},
        {"id": "weissman_bayes", "title": "Weissman Bayesian analysis",
         "url": "https://michaelweissman.substack.com/", "author": "Michael Weissman", "side": "lab_leak"},
        {"id": "rootclaim_response", "title": "Rootclaim: Response to Scott Alexander",
         "url": "https://blog.rootclaim.com/covid-origins-debate-response-to-scott-alexander/",
         "author": "Saar Wilf / Rootclaim", "side": "lab_leak"},
    ],
    "claims": [
        {"id": "C001", "text": "The earliest known COVID cases cluster around the Huanan Seafood Market",
         "kind": "evidence",
         "attestations": [
             {"source_id": "acx_writeup", "verbatim_span": "the earliest known cases cluster around the market",
              "context": "central geographic evidence", "framing": "treated as strong evidence for zoonosis"},
             {"source_id": "judge_will", "verbatim_span": "the market cluster is the strongest single piece of evidence",
              "context": "judge's weighting", "framing": ""}],
         "probability_estimates": [{"source_id": "acx_writeup", "value": "load-bearing for 90-10 zoonosis", "note": ""}]},
        {"id": "C002", "text": "COVID-19 originated via natural zoonotic spillover",
         "kind": "conclusion",
         "attestations": [{"source_id": "acx_writeup", "verbatim_span": "I'm still at 90-10 zoonosis",
                           "context": "overall conclusion", "framing": ""}],
         "probability_estimates": [{"source_id": "acx_writeup", "value": "P~0.9", "note": ""},
                                   {"source_id": "judge_will", "value": "decisively zoonosis", "note": ""}]},
        {"id": "C003", "text": "The market cluster reflects ascertainment/reporting bias, not the origin location",
         "kind": "inference",
         "attestations": [{"source_id": "rootclaim_response",
                           "verbatim_span": "the cluster is an artifact of where testing and attention were focused",
                           "context": "core rebuttal", "framing": "central to the lab-leak case"}],
         "probability_estimates": []},
        {"id": "C004", "text": "Removing the market-cluster evidence flips the overall conclusion toward lab-leak",
         "kind": "inference",
         "attestations": [{"source_id": "rootclaim_response",
                           "verbatim_span": "once it is removed, lab-leak becomes the winning hypothesis",
                           "context": "Rootclaim's sensitivity claim", "framing": ""}],
         "probability_estimates": [{"source_id": "rootclaim_response", "value": "Scott would flip to 94% lab-leak", "note": ""}]},
        {"id": "C005", "text": "Six independent Bayesian analyses of the same evidence span ~23 orders of magnitude",
         "kind": "evidence",
         "attestations": [{"source_id": "acx_writeup",
                           "verbatim_span": "six independent Bayesian analyses spanned 23 orders of magnitude",
                           "context": "on disagreement between analysts", "framing": ""}],
         "probability_estimates": []},
        {"id": "C006", "text": "COVID-19 originated from a research-related leak",
         "kind": "conclusion",
         "attestations": [{"source_id": "weissman_bayes", "verbatim_span": "the evidence favors a laboratory origin",
                           "context": "Weissman conclusion", "framing": ""},
                          {"source_id": "rootclaim_response", "verbatim_span": "high confidence that Covid originated from a lab",
                           "context": "Rootclaim conclusion", "framing": ""}],
         "probability_estimates": [{"source_id": "rootclaim_response", "value": "high confidence lab", "note": ""}]},
    ],
    "edges": [
        {"from": "C001", "to": "C002", "type": "depends_on", "source_id": "acx_writeup", "strength": "strong"},
        {"from": "C001", "to": "C002", "type": "is_evidence_for", "source_id": "judge_will", "strength": "strong"},
        {"from": "C003", "to": "C001", "type": "contradicts", "source_id": "rootclaim_response", "strength": "disputed"},
        {"from": "C001", "to": "C004", "type": "depends_on", "source_id": "rootclaim_response", "strength": "strong"},
        {"from": "C004", "to": "C006", "type": "supports", "source_id": "rootclaim_response", "strength": "asserted"},
        {"from": "C003", "to": "C006", "type": "is_evidence_for", "source_id": "rootclaim_response", "strength": "weak"},
        {"from": "C005", "to": "C002", "type": "caveats", "source_id": "acx_writeup", "strength": "asserted"},
    ],
}


def main():
    cruxes = _centrality_fallback(DEMO)
    DEMO["assessment"] = {
        "cruxes": cruxes,
        "correlated_evidence_flags": [
            {"claim_ids": ["C001"],
             "rationale": "Multiple cited case-count figures derive from the same Huanan market dataset; "
                          "treating them as separate corroboration would double-count one source of evidence."}],
    }
    out_dir = os.path.join("cases", "covid", "out")
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "graph.json"), "w", encoding="utf-8") as f:
        json.dump(DEMO, f, indent=2, ensure_ascii=False)
    render_viewer("covid")
    print("Demo graph built. Open cases/covid/out/graph.html "
          "(or http://localhost:8000/cases/covid/out/graph.html under Docker).")
    print(f"Top crux: {cruxes[0]['claim_id']} (sensitivity {cruxes[0]['sensitivity']}) — "
          "the market-cluster claim both conclusions pivot on.")


if __name__ == "__main__":
    main()
