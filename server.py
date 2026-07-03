"""Static server for the Epistemic Stack web app — same command locally and in deployment.

Serves the interrogable viewer (web/) plus the pre-built case data (web/data/). Binds to $PORT
so `python server.py` runs identically on a laptop and on a PaaS (Railway / Render / Fly) via the
Procfile. No API key, no LLM calls, no database — it only serves already-computed graphs, so there
is no running cost and no abuse surface. Regenerate the data after a pipeline run with
`python web/build_data.py`.
"""
import functools
import http.server
import os

PORT = int(os.environ.get("PORT", "8000"))
WEB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")


def main():
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=WEB_DIR)
    print(f"Epistemic Stack on http://0.0.0.0:{PORT}  (serving {WEB_DIR})")
    http.server.ThreadingHTTPServer(("0.0.0.0", PORT), handler).serve_forever()


if __name__ == "__main__":
    main()
