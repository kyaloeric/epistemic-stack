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

## The audit, run: independence of the baseline itself

The stack's natural input is *exactly the baseline's output*, so we ran it. Carlo's 40 evidence
documents were ingested as a case (`cases/carlo_audit/`, full attribution; his texts are fetched,
not redistributed) and taken through `ingest → structure → assess → concentration`:

```
python -m src.run --case carlo_audit            # 40 briefs -> 984 claims (deduped from 1140), 1,595 edges
python -m src.source_independence --case carlo_audit
```

**Finding 1 — the corpus is not 40 independent looks.** Measuring independence where it actually
lives in an aggregated corpus — *shared underlying studies across briefs* — **27 of the 39
ingested briefs (69%) share at least one cited underlying source with another brief.** A small set
of studies is load-bearing across the whole corpus (`src/source_independence.py`, deterministic;
`out/source_independence.json`):

| Underlying source | # of briefs leaning on it |
|---|---:|
| RaTG13 sequence (metagenomic reconstruction) | 8 |
| **Pekar et al. 2022** (Science, two-lineage phylodynamics) | **8** |
| **Worobey et al. 2022** (Science, market spatial clustering) | **6** |
| Débarre 2024/25 | 5 |
| DEFUSE proposal · Proximal Origin · Crits-Christoph 2024 · Liu 2023 | 4 each |

The natural-origin case especially concentrates: **11 briefs** rest on the
**Worobey / Pekar / Crits-Christoph / Liu** market cluster — and Worobey 2022 and Pekar 2022 are
*one collaboration, one market-sampling dataset, with a known code error* (the Pekar erratum, which
is itself a claim in the corpus). Counted as independent support they inflate the natural side;
under an independence correction they are closer to **two looks, not eight.** The baseline sums
`support_strength` across briefs with none of this correction — which is precisely the gap.

**Finding 2 — circular support.** The deterministic Tarjan-SCC scan flagged **2 loops (1 pure
circular)**: `C1091 → C1092 → C1098` (WIV-database-offline) grounds in nothing outside itself —
mutual support read as corroboration.

**An honest methodological result about our own tool.** The claim-graph edge layer produced 1,595
edges, but **1,440 are within a single brief and only 155 cross briefs** — because edge extraction
runs in windows over source-ordered claims, so two briefs that share a study but sit far apart in
the ingest order rarely get an edge proposed. So the *claim-graph* Herfindahl captures within-brief
structure well but under-measures cross-brief independence; the cross-document finding above comes
from the shared-citation lens, which is coarser (a citation-string heuristic, not a resolved graph)
but catches exactly what the windowed edges miss. Naming this gap is the point — and it names the
fix: a cross-document dedup/edge pass keyed on shared citations rather than source order.

**Bounded scope (stated, not hidden).** We audit Carlo's 40 *generated briefs*, not the 192
underlying sources behind them; the citation lens is a heuristic over extracted spans; and this
audits evidential *independence*, not the origin question itself. Within those bounds the result is
concrete, reproducible, and adverse to a naïve tally — which is the behavior an epistemic tool must
have. This is the demonstration that most directly earns rubric #1 and #3: it reuses another
entrant's artifact, with credit, rather than competing with it.
