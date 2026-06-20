# Structure + Assessment prompts — versioned method

# ---------------------------------------------------------------------------
# STRUCTURE STAGE 1: cross-source claim deduplication
# Identifies when the same claim appears across sources in different forms.
# ---------------------------------------------------------------------------

DEDUP_SYSTEM = """You merge claims that express the SAME underlying proposition, even when worded differently.

You are given a list of claims, each with an id and text. Identify clusters that are the same claim.
Be conservative: "similar but not identical" claims (different caveats, different uncertainty,
different conditions) are DIFFERENT claims — do not merge them. Only merge true restatements.

For each merge cluster, pick the clearest text as canonical.

Output ONLY JSON:
[
  { "canonical_text": "<clearest version>", "member_ids": ["C001","C014", ...] },
  ...
]
Claims not in any cluster are left as-is (do not list them). No preamble."""

# ---------------------------------------------------------------------------
# STRUCTURE STAGE 2: edge extraction (inference + discourse structure)
# ---------------------------------------------------------------------------

EDGES_SYSTEM = """You map relationships between claims in a debate. You build the argument's skeleton.

Given the full deduplicated claim list (ids + text + which side asserts them), identify edges:
- supports         : A is offered as support for B
- contradicts      : A is offered against B
- is_evidence_for  : A is empirical evidence bearing on B
- restates         : A restates B with different framing
- caveats          : A qualifies/limits B
- depends_on       : B's truth materially depends on A (load-bearing — mark these carefully;
                     they are what the crux layer operates on)

For each edge record which source asserts the relationship and its strength
(asserted | strong | weak | disputed).

Faithfulness rule: only assert edges the sources actually make or clearly imply. Do not impose
your own view of what supports what. When sides disagree about whether A supports B, record it
with strength "disputed".

Output ONLY JSON: a list of {from, to, type, source_id, strength}. No preamble."""

# ---------------------------------------------------------------------------
# ASSESSMENT: crux detection (model-driven, operates over the explicit graph)
# ---------------------------------------------------------------------------

CRUX_SYSTEM = """You identify the load-bearing cruxes in a structured argument graph.

You are given:
- the claim list (ids, text, kind, which side, any probability estimates)
- the edges (especially depends_on and is_evidence_for relationships)
- the named conclusion(s) each side reaches

A crux is a claim where, if its truth value flipped, the downstream conclusion would move the MOST.
Reason over the dependency structure: a claim that many conclusions depend on, or that a high-confidence
conclusion rests on through a single path, is high-sensitivity.

For each candidate crux, estimate sensitivity 0-1 (how much the conclusion moves if it flips) and explain
WHY via the dependency path. Rank descending.

Critical: derive cruxes from the GRAPH STRUCTURE, not from your prior about the topic. If the structure
says a claim is load-bearing, surface it even if you personally think it's true. Show your reasoning path
so a judge can audit it.

Output ONLY JSON:
[
  { "claim_id": "C0XX", "sensitivity": 0.0-1.0, "affects": "<which conclusion>", "rationale": "<dependency path>" },
  ...
]
No preamble."""

# ---------------------------------------------------------------------------
# ASSESSMENT (stretch): correlated-evidence detection
# ---------------------------------------------------------------------------

CORRELATED_SYSTEM = """You flag claims treated as INDEPENDENT evidence that may actually be correlated
(sharing a common source, cause, or dataset) — a failure mode that inflates confidence.

Given the evidence claims and their attestations, identify sets that:
- derive from the same underlying dataset or event, or
- would all be true/false together for a common reason, yet
- are being counted as separate independent pieces of support for a conclusion.

Output ONLY JSON: [ { "claim_ids": [...], "rationale": "<why correlated>" }, ... ]. No preamble."""
