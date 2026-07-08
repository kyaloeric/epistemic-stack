# FLF Epistemic Case Study Competition — Submission Index

**Eric Kyalo · solo · Nairobi, Kenya**
Early-feedback (June 21) submission; full build by July 19.

This repo is the executable half of the submission. The written core (≤10 pages) is
[`PRIMARY.md`](PRIMARY.md). Use the reading-budget map below.

## Reading-budget map (≤10 pages of attention)

1. **Open the interrogable web app** (`docker compose up` → http://localhost:8000, or `python server.py`)
   — the artifact: click any claim to trace its verbatim provenance and dependencies; deterministic
   crux ranking, per-conclusion concentration + effective-independent count, and circular-support checks.
2. **`prompts/ingest.py`, `prompts/structure_assess.py`** — the method (the prompts are the product).
3. **`baseline/market_cluster_subq/delta.md`** — the head-to-head vs deep research.
4. **`src/assess.py` + `src/concentration.py`** — deterministic crux detection (graph concentration,
   Herfindahl effective-count, Tarjan-SCC circular-support). The numbers are computed, not model-generated.
5. **`tests/adversarial.md`** — attack→defense table + named failure modes.

## Run it

**View the artifact (no API key, ~1 min):**
```bash
docker compose up                       # then open http://localhost:8000
# or, without Docker:
pip install -r requirements.txt --break-system-packages
python web/build_data.py && python server.py   # serves the interrogable app on :8000
```

**Live pipeline (needs key + source texts):**
```bash
export ANTHROPIC_API_KEY=sk-...
# drop cleaned source text into cases/covid/raw/<source_id>.txt (ids in cases/covid/sources.json)
python -m src.run --case covid
python -m src.run --case blackholes
python -m src.run --case eggs
```

## What's done vs. in progress

- [x] Pipeline architecture (ingest → structure → assess), versioned prompts, JSON schema
- [x] Navigable HTML viewer with provenance + crux panel
- [x] Deterministic crux fallback (tested) + offline demo graph for COVID
- [x] Three case manifests (COVID deep; black holes; eggs) for the generalization claim
- [x] Baseline-comparison and adversarial-test templates
- [ ] Live LLM extraction over the real sources (needs your key)
- [ ] Completed baseline delta + adversarial results (after live run)
- [ ] Written ≤10-page core finalized in the Primary Document

## Layout

```
src/        pipeline stages + offline demo + runner
prompts/    the LLM prompts (the method)
schema/     claim-graph JSON schema
cases/      per-case source manifests + outputs
viewer/     static HTML graph viewer
baseline/   deep-research vs pipeline comparison
tests/      adversarial robustness exercises
Dockerfile, docker-compose.yml   one-command demo
```

MIT licensed, so pieces can interoperate and compound — per the competition's goals.
