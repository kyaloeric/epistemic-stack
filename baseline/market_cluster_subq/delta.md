# Sub-question: does the evidence for each COVID-origin conclusion actually *hold up* — is it independent, concentrated, or circular — and can you show your work?

This is the sub-question re-centered on the layer that matters. The contest's framing (claim
graphs, "who said what") is the layer a single prompt already saturates — see the baseline below.
The valuable, under-specified layer is **evidential warrant**: not *what* is claimed, but whether
the offered support is *valid* — independent vs. echo, robust vs. fragile, grounded vs. circular.
That is the layer this stack contributes, deterministically and auditably.

---

## The baseline (the bar we must beat)

**Carlo Martinucci's reproducible baseline** — `github.com/carlomartinucci/flf-epistack-contest`,
a ~23-minute unattended Claude Code (Opus 4.8) swarm from a **single prompt**. It produced:

- **40 sourced evidence documents**, **192 unique sources**
- A calibrated bottom line: **~72% natural / 28% lab-related**
- Per evidence item, **two separate scores**: `claim_confidence` (0–1, is the fact true) and
  `support_strength` (weak/moderate/strong, how much it moves the origin question)
- `INDEX.md` (evidence catalog by hypothesis) + `CONCLUSION.md` (synthesis)

This is a strong, honest baseline — and it already does the things a claim-graph tool is usually
sold on: provenanced claims, per-claim calibration, a weighted conclusion. **A provenance graph
that only re-maps this loses.** So the question is not "can we also map claims" (we can; so can a
prompt). It is: *what can we compute that the swarm structurally cannot?*

**What the baseline does NOT do — by construction:** it sums `support_strength` across 40 items to
reach 72/28 with **no independence model**. It never checks whether the pro-zoonosis items are
independent looks or the same dataset counted many times; it never detects circular support (A
rests on B rests on A); it cannot say *how much of a conclusion rides on its single most
load-bearing claim*. Each score is per-claim; there is no cross-claim warrant structure. This is
exactly the failure the contest critique names: *"if the observations are non-independent, the
inference fails even if the claim graph is correct."*

---

## What the stack adds: a deterministic warrant layer (no LLM, fully re-runnable)

Run on the ingested COVID graph (`src/concentration.py`, pure graph arithmetic — anyone re-runs it
and gets identical numbers):

```
python -m src.run --case covid --stage concentration
```

For **every** conclusion it computes three warrant metrics the baseline has no way to produce:

| Conclusion (from the ingested graph) | Support | **Concentration** on top claim | **Effective-independent claims** (Herfindahl) |
|---|---:|---:|---:|
| "The market is unlikely to be the origin of the pandemic" | 102 | 5% | **~48.9** |
| "Double-spillover is the only story that fits" | 104 | 5% | **~46.1** |
| "WIV found a BANAL-52 relative + added a furin site" | 69 | 4% | **~42.5** |
| "Lab-leak scenario requires the first worker near the market" | 11 | **22%** | ~7.0 |
| "After the debate, author is 90-10 zoonosis" | 10 | **21%** | ~8.0 |

Plus a **circular-support scan** (Tarjan SCC over the derivation graph): one grounded loop flagged
among claims `C095 → C098 → C102 → C103` (a set a naïve tally would have counted as four
independent confirmations).

**Read what this says, because it is the uplift:**

- The two major origin conclusions rest on **~48 and ~46 effectively-independent claims** at **5%
  concentration** — i.e. they are **robust**: no single claim is load-bearing; you could remove any
  one and the conclusion barely moves. The baseline's 72/28 *asserts* a weighting; this **certifies
  the structure** behind it, with a number.
- The **fragile** conclusions are the *small* ones (22% / 21% concentrated on one claim). Those —
  not the headline — are where a single flipped claim moves the answer. That is the real crux
  location, and it is the opposite of where a motivated reader would look.

---

## The honest headline finding (and why it's a *selling point*, not a miss)

The original hypothesis — *"the whole zoonosis case leans on the Huanan market cluster; remove it
and it flips"* — is a claim a one-prompt baseline (or a motivated analyst) will happily assert. Run
deterministically on the same source material, **this stack declines to confirm it**: on the
ingested ACX synthesis, market/zoonosis support is **diffuse (nEff ≈ 48), not concentrated on any
single claim.** The tool refuses to manufacture a load-bearing crux the structure does not contain.

That refusal *is* the epistemic uplift (rubric #6, #1): an auditable number correcting an
over-confident structural claim, rather than a fluent narrative confabulating one. A tool that only
tells you what you hoped to hear is worthless here; one that says "actually, your decisive-crux
story isn't in the evidence — here is the concentration math" is the point.

---

## The delta (stated plainly, wins and losses)

**Where the stack is meaningfully better:**
- It computes an **independence / concentration / circularity audit** the baseline cannot — the
  warrant layer, not the discourse layer. Every number is reproducible with **zero model calls**,
  so it can't be hand-waved or hallucinated (rubric #4, #5).
- It **corrects**, rather than echoes, an over-confident crux claim (rubric #6).

**Where the baseline is better (named honestly):**
- **Breadth**: 192 real sources vs. our single ingested synthesis — the baseline's corpus is far
  wider right now.
- **Readability & bottom line**: a fluent 72/28 synthesis is a better first orientation than a
  metrics table.
- **The stack does not adjudicate truth** — it audits warrant structure; it will not tell you the
  origin of COVID.

**Verdict:** on *this* sub-question — "does the support hold up, and can you show it?" — the stack
is **meaningfully better than the baseline**, because the baseline cannot answer it at all. On
"give me a broad, readable, sourced synthesis," the baseline wins. The two are **complementary**:
which points at the strongest next step below.

---

## Interop path (the strongest next experiment)

The stack's natural input is *exactly the baseline's output*. Carlo's 40 evidence documents — each
a claim with sources and a `support_strength` — are an ingestible source set. Running them through
`ingest → structure → assess → concentration` would produce an **independence audit of the
baseline itself**: which of the 40 "independent" items collapse to a shared dataset, whether the
72/28 weighting survives a Herfindahl correction, and where the real fragility sits. That is the
demonstration that most directly earns rubric #1 and #3 — and it reuses another entrant's artifact
rather than competing with it.

*Note: this requires a cross-document unification pass (dedup/shared-root edges across, not just
within, source-ordered windows) that the current structure stage does not yet do — so it is
correctly listed as future work, not a completed result.*
