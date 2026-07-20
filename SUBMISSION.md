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
- [x] Live extraction over the real sources — **eggs** (202 claims, 220 edges, 35 cross-source) and
      **COVID** (1,590 claims, 4,435 edges, 1,198 cross-source / 820 cross-side), both pipeline-produced
- [x] **Semantic candidate selection** (`src/semantic.py`) — deterministic TF-IDF/topic grouping that
      scales edge extraction past the positional windowing limit (PRIMARY §5/§6)
- [x] Relay provider (`src/llm.py`) + additive edge-merge (`src/merge_edges.py`) — run the pipeline with
      no billed API key; import/validate an edge set against existing claims
- [x] Written ≤10-page core finalized in `PRIMARY.md`
- [ ] **Black holes not ingested** — curated and fetched only (manifest + raw texts present)
- [ ] Baseline delta and adversarial results are written up from the eggs run; not re-run against COVID

## Layout

```
src/        pipeline stages: fetch, ingest, structure, assess, concentration, warrant, run
prompts/    the LLM prompts (the method)
schema/     claim-graph JSON schema
cases/      per-case source manifests + outputs (raw texts are fetched, never committed)
web/        interrogable app: claim index, provenance, support tree, warrant panels
server.py   dependency-free server for web/ + POST /api/assess (audit any claim graph, no key)
baseline/   baseline comparison and delta analysis
tests/      adversarial robustness exercises
Dockerfile, docker-compose.yml   one-command demo
```

MIT licensed, so pieces can interoperate and compound — per the competition's goals.
