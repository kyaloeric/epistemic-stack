"""Pipeline runner. One command per case.

    python -m src.run --case covid                # full pipeline
    python -m src.run --case covid --stage ingest # single stage
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from src.ingest import ingest  # noqa: E402
from src.structure import structure  # noqa: E402
from src.assess import assess  # noqa: E402


def render_viewer(case: str, root: str = "."):
    """Inline the graph into the static HTML viewer for a self-contained shareable artifact."""
    case_dir = os.path.join(root, "cases", case)
    graph_path = os.path.join(case_dir, "out", "graph.json")
    if not os.path.exists(graph_path):
        print("  [skip] no graph.json to render")
        return
    with open(graph_path, encoding="utf-8") as f:
        graph = f.read()
    with open(os.path.join(root, "viewer", "template.html"), encoding="utf-8") as f:
        tmpl = f.read()
    import re
    html = re.sub(r"/\*__GRAPH_DATA__\*/.*?/\*__END__\*/",
                  lambda _: graph, tmpl, flags=re.DOTALL)
    out = os.path.join(case_dir, "out", "graph.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  -> viewer written to {out} (open in a browser)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", required=True, help="covid | blackholes | eggs")
    ap.add_argument("--stage", default="all",
                    choices=["all", "ingest", "structure", "assess", "viewer"])
    ap.add_argument("--root", default=".")
    args = ap.parse_args()

    print(f"== Epistemic Stack :: case={args.case} stage={args.stage} ==")
    if args.stage in ("all", "ingest"):
        print("[1/3] INGESTION"); ingest(args.case, args.root)
    if args.stage in ("all", "structure"):
        print("[2/3] STRUCTURE"); structure(args.case, args.root)
    if args.stage in ("all", "assess"):
        print("[3/3] ASSESSMENT"); assess(args.case, args.root)
    if args.stage in ("all", "viewer"):
        print("[+] VIEWER"); render_viewer(args.case, args.root)
    print("== done ==")


if __name__ == "__main__":
    main()
