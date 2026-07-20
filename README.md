# Epistemic Stack — claim-level provenance & crux detection

A repeatable pipeline that turns a messy, multi-source dispute into a **claim-level,
fully-provenanced, navigable knowledge graph**, then surfaces the **load-bearing cruxes** —
the few claims that, if they flipped, would most change the conclusion.

Built for the FLF Epistemic Case Study Competition (solo entry). Demonstrated on three
cases of deliberately different shape: COVID-19 origins (contested), LHC black holes
(confident answer, complex evidence), and dietary eggs (mundane-but-contested).

---

## ▶ Judges start here (reading-budget map)

You have a ~10-page attention budget. Spend it in this order:

1. **`covid_graph_demo.html`** (2 min) — open in a browser. The artifact itself: claims by
   side, verbatim provenance on each, and the crux panel ranking the load-bearing Huanan-market
   claim #1. This is what the method *produces*.
2. **`prompts/ingest.py` + `prompts/structure_assess.py`** (3 pages) — the method is the prompts.
   These are the most informative code to inspect; the Python is just orchestration around them.
3. **`baseline/<subq>/delta.md`** (2 pages) — the head-to-head vs deep research on the
   "how load-bearing is the market cluster?" sub-question. This is the "meaningfully better
   than off-the-shelf" evidence.
4. **`src/assess.py`** (2 pages) — crux detection. A graph-native **Analysis of Competing
   Hypotheses** (Heuer): weight evidence by diagnosticity, computed over the dependency graph,
   with a deterministic centrality fallback so it never returns nothing.
5. **`tests/adversarial.md`** (1 page) — named failure modes and the injected-misleading-source test.

Most informative single invocation to run yourself: `python -m src.run --case covid`
(needs `ANTHROPIC_API_KEY` + source texts in `cases/covid/raw/`; or `docker compose up` for a
fresh-machine demo — see below).

---


## Why this exists

Off-the-shelf deep research produces fluent narrative summaries tuned to one reader.
They don't travel, combine, or survive adversarial scrutiny. This pipeline produces a
**structured artifact** instead: every claim links to a verbatim source span, disagreement
is represented faithfully rather than resolved, and the tool flags which claims are
actually driving each side's conclusion.

The design bet: **structure-before-assess**. Build the provenanced claim graph first,
then run assessment over the explicit structure — not over prose.

## The three layers

```
INGESTION   raw sources ──► atomic claims + provenance metadata + cross-source dedup
STRUCTURE   claims ──► typed claim graph (supports / contradicts / restates / caveats)
ASSESSMENT  graph ──► crux ranking (+ correlated-evidence flags, stretch)
```

No single hand-designed human step is load-bearing: every stage is an automated LLM
pass, so the pipeline improves as base models improve. A human curates and steers but is
not in the critical path.

## Quickstart

```bash
pip install -r requirements.txt --break-system-packages
export ANTHROPIC_API_KEY=sk-...           # your key
python -m src.run --case covid            # full pipeline on the COVID case
python -m src.run --case blackholes
python -m src.run --case eggs
```

Outputs land in `cases/<case>/out/`:
- `claims.json`        — extracted claims with provenance
- `graph.json`         — the typed claim graph
- `cruxes.json`        — ranked load-bearing claims
- `concentration.json` — per-conclusion concentration + effective-independent count + circular flags

Then view them in the interrogable web app:
```bash
python web/build_data.py && python server.py   # -> http://localhost:8000
```

## Why it generalizes (domain-agnostic by construction)

The engine never looks at domain content. Every stage operates on one abstract ontology —
**claim, edge (typed relation), conclusion, source** — and the assessment math (concentration,
Herfindahl effective-independent-count, SCC circular-support detection) is pure graph arithmetic
over that ontology. Nothing in `src/` knows what "furin cleavage site" or "dietary cholesterol"
means. What differs per dispute lives entirely in the per-case `sources.json` and the extracted
graph, not in code. That is why the identical pipeline runs a virology dispute (COVID), a physics
dispute (LHC black holes), and a nutrition dispute (eggs): a new field adds sources, never code.

## What resists being gamed (deterministic core)

The load-bearing numbers are **computed, not generated**:
- **Crux sensitivity** = a claim's share of a conclusion's evidential support (`src/assess.py`,
  `src/concentration.py`) — reproducible graph arithmetic; the LLM only writes the narration.
- **Effective-independent-count** (Herfindahl numbers-equivalent): piling correlated support on
  one root pushes a conclusion *toward 1 effective look, not up*.
- **Circular-support detection** (strongly-connected-component collapse): mutual-support loops
  that ground in nothing are flagged as one look, loudly, not counted as corroboration.

So an adversary flooding a side with restatements, shared-root reuse, or citation rings makes it
look *less* independent, never more. See `tests/adversarial.md` for the full attack→defense table.

## Baseline comparison

The competition bar is "meaningfully better than off-the-shelf deep research / Claude Code."
`baseline/` holds the side-by-side: for chosen sub-questions, the deep-research output and
the pipeline output, with a short delta analysis. See `baseline/README.md`.

## Adversarial test

`tests/adversarial.md` documents the motivated-read and injected-misleading-source
exercises, and the named failure modes (where the pipeline can be fooled).

## Repo layout

```
src/            pipeline stages (fetch, ingest, structure, assess, concentration, warrant, run)
prompts/        the LLM prompts for each stage (versioned, the real method)
schema/         JSON schema for claims and the graph
cases/          per-case source manifests + outputs (raw texts are fetched, not committed)
web/            interrogable web app: claim index, provenance, support tree, warrant panels
server.py       dependency-free server for web/ + POST /api/assess (bring-your-own graph)
baseline/       baseline comparison and delta analysis
tests/          adversarial robustness exercises
```

## Status

All three cases run end-to-end through the identical pipeline — ingestion, dedup,
structure, semantic cross-source edges, assessment, concentration:

| case | shape | claims | edges | cross-source | spans verified |
|---|---|---|---|---|---|
| COVID | curated debate | 1,590 | 4,435 | 1,198 (27%) | 95.3% |
| eggs | mundane-but-contested | 202 | 220 | 35 (16%) | 100% |
| black holes | confident answer, complex evidence | 157 | 363 | 165 (45%) | 100% |

`src/verify_spans.py` re-reads the sources and checks every `verbatim_span` is a literal
substring — that is where the 95.3% comes from, and the 76 COVID misses are listed rather
than hidden.

This is a competition prototype, not a product — optimised for legibility and
reproducibility over features.

## License

MIT (so submissions can interoperate and compound, per the competition's goals).
