# Adversarial robustness — exercises and named failure modes

Scored under rubric dimension #6: outputs must withstand motivated reading and
downstream-model interrogation, and the methodology must resist sources optimizing to mislead.

## Exercise 1 — Motivated read

Take the finished COVID graph and prompt a model to argue *against* it from each side:
- "You believe lab-leak. Find every place this structure under-weights your evidence."
- "You believe zoonosis. Same."

Record what the attack surfaces. Strong outcome: the structure already *contains* both sides'
claims with provenance, so motivated reading mostly relocates emphasis rather than finding
hidden gaps. Weak outcome: the attack finds whole claims/relations we missed — log them.

## Exercise 2 — Injected misleading source

Add a fabricated-but-plausible source that asserts a confident false claim with fake
corroboration. Run ingestion. Check:
- Does provenance isolate it? (Every claim from it is tagged to that source.)
- Does correlated-evidence flagging catch the fake corroboration as non-independent?
- Does the crux layer over-weight it?

Record whether the structure contains the damage. This tests "resists being gamed."

## Exercise 3 — Source-side gaming

Reorder / re-emphasise a real source to inflate one claim's apparent support. Check whether
the graph's edge-strength and attestation count reflect actual support or just repetition.

## Named failure modes (to state plainly in the write-up)

- **Extraction misses implicit claims** that a domain expert would infer. The pipeline only
  structures what's stated or clearly implied.
- **Dedup can over-merge** subtly different claims, collapsing a real distinction; we tuned
  conservative, but this trades off against graph clutter.
- **Crux sensitivity is an estimate**, not a proof; the centrality fallback is coarser still.
- **Garbage-in**: if all sources share a hidden common bias, the structure faithfully
  reproduces it. Provenance makes this auditable but does not correct it.
- **No ground-truth oracle**: the tool structures and surfaces; it does not adjudicate truth.

Stating these is itself scored (rubric #5, #6): bounded, named uncertainty beats hidden weakness.
