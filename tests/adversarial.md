# Adversarial robustness — attack→defense and named failure modes

Scored under rubric dimension #6: outputs must withstand motivated reading and downstream-model
interrogation, and the methodology must resist sources optimizing to mislead. The design stance:
**the load-bearing numbers are deterministic graph arithmetic, not model output** — so an attacker
has to beat the math, not just the prompt.

## Attack → defense table

| Attack | What the attacker wants | Defense in this pipeline |
|---|---|---|
| **Flood one side with restatements** of the same claim | Inflate apparent support by volume | Dedup merges true restatements; concentration attributes merged claims to one node, so effective-independent-count does **not** rise. |
| **Cohort / shared-root reuse** — many claims that all `depend_on` one upstream claim | Look like many independent supports | `concentration.py` folds dependents into the shared root; the Herfindahl effective-count collapses toward 1. |
| **Circular corroboration** — claim A supports B, B supports A, grounded in nothing | Manufacture confirmation from nowhere | Deterministic SCC (`circular_support_flags`) detects the loop, collapses it to one look, and raises a **`pure-circular` flag** naming the members. |
| **Frame-as-evidence** — restate a claim in loaded language and assert it contradicts the other side | Make a framing disagreement look like new evidence | `context_mutation` / `restates` / `caveats` edges are **excluded from evidential weight** by construction. |
| **Injected misleading source** with confident false claims + fake self-corroboration | Poison the graph, inflate a crux | Provenance isolates every claim to its source; the fake internal corroboration trips the SCC/circular detector rather than counting as independent support. |
| **Prompt-game the model** into naming a favorable crux | Bias the headline result | Crux **sensitivity is computed deterministically** from support-share; the model only writes the narration and cannot change the ranking or score. |
| **Repetition-as-support** — reassert one claim across many paragraphs of one source | Inflate edge/attestation counts | Attestations are provenance, not weight; concentration weights by graph support structure, not by how many times a source repeats itself. |

## Exercises

**E1 — Motivated read.** Prompt a model to argue against the finished COVID graph from each side
("you believe lab-leak / zoonosis — find where this under-weights your evidence"). Strong outcome:
both sides' claims already sit in the structure with provenance, so the attack relocates emphasis
rather than finding hidden gaps. Weak outcome: it surfaces whole missing claims/relations — log them.

**E2 — Injected misleading source.** Add a fabricated-but-plausible source asserting a confident
false claim with fake corroboration. Run ingestion, then check: (a) provenance isolates it;
(b) the SCC detector flags the fabricated self-corroboration as circular/non-independent;
(c) the deterministic crux does not over-weight it (its support-share, not its confidence, decides).

**E3 — Source-side gaming.** Reorder/re-emphasise a real source to inflate one claim's apparent
support. Verify the effective-independent-count and concentration reflect graph structure, not
repetition.

## Named failure modes (stated plainly in the write-up)

- **Extraction misses implicit claims** a domain expert would infer; the pipeline only structures
  what is stated or clearly implied.
- **Dedup can over-merge** subtly different claims, collapsing a real distinction; tuned conservative,
  which trades against graph clutter.
- **Self-reported derivation.** We know claim A rests on B only because the structure pass said so;
  an adversary who *omits* a dependency edge can look more independent than they are. The SCC defense
  catches declared loops, not hidden ones.
- **Crux sensitivity is a support-share estimate**, not a proof of counterfactual conclusion-flip.
- **Garbage-in**: if all sources share a hidden common bias, the structure faithfully reproduces it.
  Provenance makes this auditable but does not correct it.
- **No ground-truth oracle**: the tool structures and surfaces; it does not adjudicate truth.

Stating these is itself scored (rubric #5, #6): bounded, named uncertainty beats hidden weakness.
