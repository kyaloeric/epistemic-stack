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
- [x] Live extraction over the real sources — **eggs** end-to-end and fully automated (202 claims, 220
      edges, 35 cross-source); **COVID** run at scale (1,590 claims, 1,435 edges, 190 cross-source)
- [x] Additive edge-merge tool (`src/merge_edges.py`) — import an external edge set with no API key
- [x] Written ≤10-page core finalized in `PRIMARY.md`
- [ ] **Black holes not ingested** — curated and fetched only (manifest + raw texts present)
- [ ] **Semantic candidate selection for edge extraction** — the named scaling gap (PRIMARY §5/§6).
      COVID's cross-source edges came from a hand-run semantic pass over the conclusion layer, not from
      the automated windowed pass, which returns only 14 of 1,258 at that corpus size
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
