"""Deterministic warrant assessment over an in-memory claim graph — no LLM, no file IO.

This is the single source of truth for the warrant numbers. Both entry points use it:
  - the CLI assess stage (src/assess.py), and
  - the web endpoint (server.py) that audits a user-supplied graph live.

Given a graph {claims, edges} it produces cruxes + per-conclusion concentration +
circular-support flags, in the exact bundle shape the viewer (web/build_data.py) emits.
Because it is pure graph arithmetic, the same input yields identical numbers everywhere —
which is the whole point: the metrics are reproducible, not model-generated.
"""
import math

from src.concentration import concentration_for, circular_support_flags

VALID_KINDS = {"evidence", "inference", "assumption", "conclusion", "methodological"}
VALID_EDGE_TYPES = {"supports", "contradicts", "is_evidence_for", "restates",
                    "caveats", "depends_on", "context_mutation"}

# a conclusion resting on fewer than this many claims is an under-developed stub, not a real
# node with a crux — its lone supporters are trivially "100% load-bearing" and must not dominate.
MIN_CONCLUSION_SUPPORT = 3


def validate_graph(graph):
    """Raise ValueError with a human-readable message if the graph can't be assessed.

    Lenient by design: only the fields the warrant math actually needs are required
    (claim ids + kinds, edge from/to/type). Text and attestations enrich the viewer but
    are optional. Returns a list of non-fatal warnings for the caller to surface."""
    if not isinstance(graph, dict):
        raise ValueError("Top level must be a JSON object with 'claims' and 'edges'.")
    claims = graph.get("claims")
    edges = graph.get("edges")
    if not isinstance(claims, list) or not claims:
        raise ValueError("'claims' must be a non-empty list of claim objects.")
    if not isinstance(edges, list):
        raise ValueError("'edges' must be a list (use [] if there are none).")

    ids, warnings = set(), []
    for i, c in enumerate(claims):
        if not isinstance(c, dict) or not c.get("id"):
            raise ValueError(f"claims[{i}] is missing an 'id'.")
        if c["id"] in ids:
            raise ValueError(f"duplicate claim id '{c['id']}'.")
        ids.add(c["id"])
        if c.get("kind") not in VALID_KINDS:
            warnings.append(f"claim {c['id']} has kind '{c.get('kind')}' "
                            f"(expected one of {sorted(VALID_KINDS)}).")
    for i, e in enumerate(edges):
        if not isinstance(e, dict) or "from" not in e or "to" not in e:
            raise ValueError(f"edges[{i}] must have 'from' and 'to'.")
        if e.get("type") not in VALID_EDGE_TYPES:
            warnings.append(f"edge {e['from']}->{e['to']} has type '{e.get('type')}' "
                            f"(expected one of {sorted(VALID_EDGE_TYPES)}).")
        for end in ("from", "to"):
            if e[end] not in ids:
                warnings.append(f"edge references unknown claim id '{e[end]}' — ignored.")
    if not any(c.get("kind") == "conclusion" for c in claims):
        warnings.append("no claim has kind 'conclusion' — concentration is computed per "
                        "conclusion, so there will be nothing to audit. Mark your bottom-line "
                        "claim(s) with \"kind\": \"conclusion\".")
    return warnings


def deterministic_cruxes(graph):
    """A crux is a claim that carries a large share of a SUBSTANTIVELY supported conclusion.

    `sensitivity` = the largest support-share the claim holds over any qualifying conclusion
    (0-1): flip it and roughly that fraction of that conclusion's grounding goes with it. But
    share alone rewards stubs (a 1-supporter conclusion is trivially 100% concentrated), so we
    (1) skip conclusions below MIN_CONCLUSION_SUPPORT and (2) rank by `score = share *
    log2(1+supporters)` — carrying 23% of a 104-claim conclusion beats carrying 100% of a
    1-claim stub. Pure graph arithmetic, reproducible by re-running src.concentration."""
    conclusions = [c["id"] for c in graph["claims"] if c.get("kind") == "conclusion"]
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


def _normalize(graph):
    """Fill the optional fields the viewer expects so a minimal user graph still renders."""
    for c in graph.get("claims", []):
        c.setdefault("attestations", [])
        c.setdefault("text", c.get("id", ""))
    for e in graph.get("edges", []):
        e.setdefault("strength", "asserted")
        e.setdefault("source_id", "")
    return graph


def assess_graph(graph, case="uploaded"):
    """Run the full deterministic warrant audit on an in-memory graph and return the bundle
    the viewer loads (same shape as web/build_data.py). No LLM, no file IO, no randomness."""
    _normalize(graph)
    conclusions = [c["id"] for c in graph["claims"] if c.get("kind") == "conclusion"]
    cruxes = deterministic_cruxes(graph)
    circular = circular_support_flags(graph)
    concentration = [concentration_for(graph, cid) for cid in conclusions]
    return {
        "case": graph.get("case", case),
        "question": graph.get("question", ""),
        "shape": graph.get("shape", ""),
        "sources": graph.get("sources", []),
        "claims": graph["claims"],
        "edges": graph["edges"],
        "assessment": {
            "cruxes": cruxes,
            "correlated_evidence_flags": circular,
            "method": "deterministic concentration + Tarjan-SCC (in-browser upload; no LLM)",
        },
        "concentration": concentration,
        "circular_support": circular,
    }
