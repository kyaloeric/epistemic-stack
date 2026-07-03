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
from src.concentration import compute_concentration  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", required=True, help="covid | blackholes | eggs")
    ap.add_argument("--stage", default="all",
                    choices=["all", "ingest", "structure", "assess", "concentration"])
    ap.add_argument("--root", default=".")
    ap.add_argument("--limit-chunks", type=int, default=0,
                    help="smoke test: ingest only the first N chunks per source (0 = all)")
    args = ap.parse_args()

    print(f"== Epistemic Stack :: case={args.case} stage={args.stage} ==")
    if args.stage in ("all", "ingest"):
        print("[1/4] INGESTION"); ingest(args.case, args.root, args.limit_chunks)
    if args.stage in ("all", "structure"):
        print("[2/4] STRUCTURE"); structure(args.case, args.root)
    if args.stage in ("all", "assess"):
        print("[3/4] ASSESSMENT"); assess(args.case, args.root)
    if args.stage in ("all", "concentration"):
        print("[4/4] CONCENTRATION"); compute_concentration(args.case, args.root)
    print("== done ==\n   view it: python web/build_data.py && python server.py  -> http://localhost:8000")


if __name__ == "__main__":
    main()
