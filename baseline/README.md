# Baseline comparison — the bar is "meaningfully better than deep research"

The judges anchor every submission against off-the-shelf deep research and a careful
Claude Code investigation, and **run** submissions rather than just reading them. This
folder makes the comparison a first-class, reproducible artifact.

## Method

For each chosen sub-question, we capture three things:

1. **`<subq>/baseline.md`** — output of a standard deep-research / Claude-Code investigation
   on the sub-question. (Paste the raw output verbatim, with the tool and date noted.)
2. **`<subq>/pipeline.md`** — what our pipeline surfaces on the same sub-question
   (claims + provenance + crux ranking, exported from the graph).
3. **`<subq>/delta.md`** — a short, honest analysis of what the pipeline surfaces that
   the baseline misses, and equally where the baseline is *better* (faster, more fluent).

## COVID sub-questions to run

These are chosen because they expose the pipeline's strengths and are checkable:

1. **"How much of the zoonosis conclusion rests on the Huanan market cluster?"**
   - Expected pipeline edge: it identifies the market-cluster claim as the top crux from
     the dependency structure, shows which conclusions depend on it, and links every
     attestation to a verbatim span. A narrative baseline tends to *mention* the market
     evidence without quantifying how load-bearing it is.
2. **"Where do the six Bayesian analyses actually diverge?"**
   - Expected pipeline edge: probability estimates are attached to specific claims, so the
     23-orders-of-magnitude spread becomes a per-claim divergence map, not prose.
3. **"Which pieces of zoonosis evidence might be correlated rather than independent?"**
   - Expected pipeline edge: the correlated-evidence flag names candidate sets; baselines
     rarely surface this unprompted.

## Honesty rule

If the baseline matches or beats the pipeline on a sub-question, we say so in `delta.md`.
A named loss is more credible than a hidden one, and the judging rubric rewards bounded
honesty (dimensions #5 and #6).
