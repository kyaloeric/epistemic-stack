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

## Deploy (static host)
The site is pure static files. Fastest options:

- **Netlify** — drag the `web/` folder onto <https://app.netlify.com/drop> for an instant URL,
  or connect the GitHub repo (root `netlify.toml` sets `publish = web/`, no build step).
- **Vercel / Cloudflare Pages** — new project → set the output/root directory to `web`.

To refresh the deployed data after a pipeline run: `python web/build_data.py`, commit `web/data/`,
and the host redeploys.
