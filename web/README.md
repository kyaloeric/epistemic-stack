# Epistemic Stack — web app

A static, fully-interrogable viewer for the claim graphs the pipeline produces. No backend, no
API key: the app loads pre-built JSON (`web/data/`) and lets a reader trace provenance and
dependencies, inspect the deterministic crux ranking, per-conclusion concentration, and the
circular-support integrity checks.

## Run locally
```bash
python web/build_data.py          # bundle cases/<case>/out/ -> web/data/
cd web && python -m http.server 8000
# open http://localhost:8000
```

## What you can do in it
- **Left** — search/filter every claim (by side, kind, or crux); click to open one.
- **Center** — the selected claim: verbatim provenance span + source, framing, probability
  estimates, and its edges both ways ("points to" / "pointed to by"). Every related claim is
  clickable, so you can walk the dependency graph.
- **Right** — the deterministic assessment: **Cruxes** (ranked by share × log₂(1+support)),
  **Conclusions** (concentration % + effective-independent-claim count + top contributions), and
  **Integrity** (circular-support loops with severity, correlated-evidence flags).

## Deploy
Served by `server.py` (repo root) — a dependency-free Python static server that binds `$PORT`.
Same command locally and in production:

```bash
python web/build_data.py && python server.py     # local: http://localhost:8000
```

The root `Procfile` (`web: python server.py`) deploys as-is on **Railway / Render / Fly** — point
the platform at the repo, no build config needed (the data under `web/data/` is committed). To
refresh after a pipeline run: `python web/build_data.py`, commit `web/data/`, redeploy.
