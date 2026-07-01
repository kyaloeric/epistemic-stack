"""Bundle pipeline outputs into static data the deployed web app loads.

Scans cases/<case>/out/ for graph.json (+ concentration.json) and writes:
  web/data/<case>.json    — merged graph + assessment + concentration for the viewer
  web/data/manifest.json  — the case list the app's switcher reads

Pure file processing, no LLM, no network — so the deploy artifact is reproducible from the
committed case outputs. Run from repo root:  python web/build_data.py
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CASES_DIR = os.path.join(ROOT, "cases")
OUT_DIR = os.path.join(ROOT, "web", "data")


def _load(path):
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def build():
    os.makedirs(OUT_DIR, exist_ok=True)
    manifest = []
    for case in sorted(os.listdir(CASES_DIR)):
        case_dir = os.path.join(CASES_DIR, case)
        if not os.path.isdir(case_dir):
            continue
        sources_meta = _load(os.path.join(case_dir, "sources.json")) or {}
        graph = _load(os.path.join(case_dir, "out", "graph.json"))
        conc = _load(os.path.join(case_dir, "out", "concentration.json"))
        has_data = bool(graph and graph.get("claims"))

        entry = {
            "case": case,
            "question": sources_meta.get("question", ""),
            "shape": sources_meta.get("shape", ""),
            "source_count": len(sources_meta.get("sources", [])),
            "has_data": has_data,
        }
        if has_data:
            bundle = {
                "case": case,
                "question": sources_meta.get("question", ""),
                "shape": sources_meta.get("shape", ""),
                "sources": graph.get("sources", []),
                "claims": graph.get("claims", []),
                "edges": graph.get("edges", []),
                "assessment": graph.get("assessment", {}),
                "concentration": (conc or {}).get("conclusions", []),
                "circular_support": (conc or {}).get("circular_support", []),
            }
            entry["claim_count"] = len(bundle["claims"])
            entry["edge_count"] = len(bundle["edges"])
            with open(os.path.join(OUT_DIR, f"{case}.json"), "w", encoding="utf-8") as f:
                json.dump(bundle, f, ensure_ascii=False, separators=(",", ":"))
            print(f"  {case}: {entry['claim_count']} claims, {entry['edge_count']} edges -> web/data/{case}.json")
        else:
            print(f"  {case}: manifest only ({entry['source_count']} sources), not yet run")
        manifest.append(entry)

    with open(os.path.join(OUT_DIR, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(f"  -> manifest: {len(manifest)} cases written to web/data/manifest.json")


if __name__ == "__main__":
    build()
