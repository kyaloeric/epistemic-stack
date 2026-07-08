"""Server for the Epistemic Stack web app — same command locally and in deployment.

Serves the interrogable viewer (web/) plus the pre-built case data (web/data/), and exposes
ONE endpoint — POST /api/assess — that runs the deterministic warrant audit on a claim graph
the user supplies (their own Claude turned an article into claims+edges; we compute the numbers).

No API key, no LLM call, no database. The endpoint only runs pure graph arithmetic
(src/warrant.py -> src/concentration.py), so there is no token cost and no abuse surface: the
heavy, key-requiring extraction happened in the user's own Claude, not here. Binds to $PORT so
`python server.py` runs identically on a laptop and on a PaaS via the Procfile. Regenerate the
pre-built case data after a pipeline run with `python web/build_data.py`.
"""
import functools
import http.server
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from src.warrant import assess_graph, validate_graph  # noqa: E402

PORT = int(os.environ.get("PORT", "8000"))
WEB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")
MAX_UPLOAD = 8 * 1024 * 1024  # 8 MB — generous for a claim graph, bounds the abuse surface


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=WEB_DIR, **k)

    def _json(self, code, obj):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path.rstrip("/") != "/api/assess":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0 or length > MAX_UPLOAD:
            self._json(413, {"error": f"Upload must be 1 byte to {MAX_UPLOAD // (1024*1024)} MB."})
            return
        try:
            graph = json.loads(self.rfile.read(length).decode("utf-8"))
        except (ValueError, UnicodeDecodeError) as e:
            self._json(400, {"error": f"Not valid JSON: {e}"})
            return
        try:
            warnings = validate_graph(graph)
            bundle = assess_graph(graph)
        except ValueError as e:
            self._json(422, {"error": str(e)})
            return
        except Exception as e:  # never leak a stack trace to the browser
            self._json(500, {"error": f"Assessment failed: {e}"})
            return
        bundle["warnings"] = warnings
        self._json(200, bundle)


def main():
    print(f"Epistemic Stack on http://0.0.0.0:{PORT}  (serving {WEB_DIR}; POST /api/assess live)")
    http.server.ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
