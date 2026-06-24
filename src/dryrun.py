"""Dry-run ingestion: run the real extraction method with NO API key.

The play (Evgeniia's trick, our method): the keyless step prints a ready-to-paste prompt;
you run it in any Claude/ChatGPT window (your existing Premium counts); you paste the JSON
back; we validate and write it into the real claim store with stable ids + provenance.

    # 1. generate a prompt for a chunk of a source:
    python -m src.dryrun prompt --case covid --source acx_writeup --chunk cases/covid/raw/acx_writeup.txt

    # 2. paste the printed prompt into Claude, copy its JSON answer into a file, then:
    python -m src.dryrun import --case covid --source acx_writeup --json pasted.json

Repeat per source/chunk. Result accumulates in cases/<case>/out/claims.json — the same
file the live pipeline produces, so structure/assess run identically afterward.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from prompts.ingest import SYSTEM, USER_TEMPLATE  # noqa: E402


def _load_manifest(case_dir):
    with open(os.path.join(case_dir, "sources.json"), encoding="utf-8") as f:
        return json.load(f)


def _source_meta(manifest, source_id):
    for s in manifest["sources"]:
        if s["id"] == source_id:
            return s
    sys.exit(f"source '{source_id}' not in manifest. Known: "
             + ", ".join(s["id"] for s in manifest["sources"]))


def make_prompt(case, source_id, chunk_path, root="."):
    case_dir = os.path.join(root, "cases", case)
    manifest = _load_manifest(case_dir)
    src = _source_meta(manifest, source_id)
    with open(chunk_path, encoding="utf-8") as f:
        content = f.read().strip()
    # strip any leading metadata header lines (the fetcher writes # lines)
    content = "\n".join(ln for ln in content.splitlines() if not ln.startswith("#")).strip()
    if not content:
        sys.exit(f"{chunk_path} has no body text (only header/empty). Paste the article text into it first.")

    user = USER_TEMPLATE.format(
        title=src["title"], author=src.get("author", "unknown"),
        side=src.get("side", "n/a"), content=content,
    )
    sep = "=" * 70
    print(f"\n{sep}\nPASTE EVERYTHING BELOW THIS LINE INTO YOUR CLAUDE/CHATGPT WINDOW\n{sep}\n")
    print(SYSTEM)
    print("\n--- INPUT ---\n")
    print(user)
    print(f"\n{sep}\nThen save the JSON it returns to a file and run:\n"
          f"  python -m src.dryrun import --case {case} --source {source_id} --json <that_file>\n{sep}\n")


def import_json(case, source_id, json_path, root="."):
    case_dir = os.path.join(root, "cases", case)
    out_dir = os.path.join(case_dir, "out")
    os.makedirs(out_dir, exist_ok=True)
    claims_path = os.path.join(out_dir, "claims.json")

    # load what the model returned
    with open(json_path, encoding="utf-8") as f:
        raw = f.read().strip()
    # tolerate fences / preamble
    import re
    m = re.search(r"(\[.*\])", raw, re.DOTALL)
    if not m:
        sys.exit("No JSON array found in the pasted file. Paste just the model's JSON answer.")
    new_claims = json.loads(m.group(1))

    # load or init the accumulating store
    if os.path.exists(claims_path):
        with open(claims_path, encoding="utf-8") as f:
            store = json.load(f)
    else:
        manifest = _load_manifest(case_dir)
        store = {"case": case, "sources": manifest["sources"], "claims": []}

    # assign stable ids continuing from the current max
    existing = store["claims"]
    start = 1 + max([int(c["id"][1:]) for c in existing if c["id"].startswith("C")] or [0])
    added = 0
    for i, c in enumerate(new_claims):
        cid = f"C{start + i:03d}"
        store["claims"].append({
            "id": cid,
            "text": c.get("text", ""),
            "kind": c.get("kind", "evidence"),
            "attestations": [{
                "source_id": source_id,
                "verbatim_span": c.get("verbatim_span", ""),
                "context": c.get("context", ""),
                "framing": c.get("framing", ""),
            }],
            "probability_estimates": (
                [{"source_id": source_id, "value": c["probability_estimate"], "note": ""}]
                if c.get("probability_estimate") else []
            ),
        })
        added += 1

    with open(claims_path, "w", encoding="utf-8") as f:
        json.dump(store, f, indent=2, ensure_ascii=False)
    print(f"  imported {added} claims from {source_id}. Store now holds {len(store['claims'])} claims.")
    print(f"  -> {claims_path}")
    # quick provenance sanity check
    missing = [c["id"] for c in store["claims"][-added:]
               if not c["attestations"][0]["verbatim_span"].strip()]
    if missing:
        print(f"  [warn] {len(missing)} new claims have an empty verbatim span "
              f"(provenance gap): {', '.join(missing[:5])}{'...' if len(missing)>5 else ''}")
    else:
        print("  provenance check: every new claim has a verbatim span. Good.")


def _claims_brief(claims):
    lines = []
    for c in claims:
        side = c["attestations"][0]["source_id"] if c["attestations"] else "?"
        lines.append(f'{c["id"]} [{c["kind"]}] ({side}): {c["text"]}')
    return "\n".join(lines)


def structure_prompt(case, stage, root="."):
    """Print a paste-ready prompt for the structure stage (dedup or edges), keyless."""
    from prompts.structure_assess import DEDUP_SYSTEM, EDGES_SYSTEM
    case_dir = os.path.join(root, "cases", case)
    with open(os.path.join(case_dir, "out", "claims.json"), encoding="utf-8") as f:
        data = json.load(f)
    brief = _claims_brief(data["claims"])
    system = DEDUP_SYSTEM if stage == "dedup" else EDGES_SYSTEM
    sep = "=" * 70
    print(f"\n{sep}\nPASTE EVERYTHING BELOW INTO YOUR CLAUDE/CHATGPT WINDOW ({stage})\n{sep}\n")
    print(system)
    print("\n--- CLAIMS ---\n")
    print(brief)
    nextcmd = ("structure-import --stage dedup" if stage == "dedup"
               else "structure-import --stage edges")
    print(f"\n{sep}\nSave the JSON it returns, then run:\n"
          f"  python -m src.dryrun {nextcmd} --case {case} --json <file>\n{sep}\n")


def structure_import(case, stage, json_path, root="."):
    """Import dedup clusters or edges from a pasted model answer; build/update graph.json."""
    import re
    from src.structure import _apply_clusters
    case_dir = os.path.join(root, "cases", case)
    out_dir = os.path.join(case_dir, "out")
    with open(os.path.join(out_dir, "claims.json"), encoding="utf-8") as f:
        data = json.load(f)
    with open(json_path, encoding="utf-8") as f:
        raw = f.read()
    m = re.search(r"(\[.*\])", raw, re.DOTALL)
    if not m:
        sys.exit("No JSON array found in the pasted file.")
    parsed = json.loads(m.group(1))

    graph_path = os.path.join(out_dir, "graph.json")
    if stage == "dedup":
        merged, alias = _apply_clusters(data["claims"], parsed)
        graph = {"case": case, "sources": data["sources"], "claims": merged,
                 "edges": [], "_alias": alias}
        with open(graph_path, "w", encoding="utf-8") as f:
            json.dump(graph, f, indent=2, ensure_ascii=False)
        print(f"  dedup: {len(data['claims'])} claims -> {len(merged)} after merge.")
        print(f"  next: python -m src.dryrun structure-prompt --stage edges --case {case}")
    else:  # edges
        with open(graph_path, encoding="utf-8") as f:
            graph = json.load(f)
        alias = graph.get("_alias", {})
        for e in parsed:
            e["from"] = alias.get(e["from"], e["from"])
            e["to"] = alias.get(e["to"], e["to"])
        graph["edges"] = parsed
        graph.pop("_alias", None)
        with open(graph_path, "w", encoding="utf-8") as f:
            json.dump(graph, f, indent=2, ensure_ascii=False)
        print(f"  edges: {len(parsed)} relationships written.")
        print(f"  graph complete -> {graph_path}")
        print(f"  next: python -m src.dryrun assess-prompt --case {case}  (assessment layer)")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("prompt", help="print a paste-ready extraction prompt")
    p.add_argument("--case", required=True)
    p.add_argument("--source", required=True)
    p.add_argument("--chunk", required=True, help="path to a text file with the source (chunk) body")
    p.add_argument("--root", default=".")

    im = sub.add_parser("import", help="import the model's JSON answer back into the claim store")
    im.add_argument("--case", required=True)
    im.add_argument("--source", required=True)
    im.add_argument("--json", required=True, help="file containing the model's JSON output")
    im.add_argument("--root", default=".")

    sp = sub.add_parser("structure-prompt", help="paste-ready prompt for dedup or edges")
    sp.add_argument("--case", required=True)
    sp.add_argument("--stage", required=True, choices=["dedup", "edges"])
    sp.add_argument("--root", default=".")

    si = sub.add_parser("structure-import", help="import dedup clusters or edges")
    si.add_argument("--case", required=True)
    si.add_argument("--stage", required=True, choices=["dedup", "edges"])
    si.add_argument("--json", required=True)
    si.add_argument("--root", default=".")

    args = ap.parse_args()
    if args.cmd == "prompt":
        make_prompt(args.case, args.source, args.chunk, args.root)
    elif args.cmd == "import":
        import_json(args.case, args.source, args.json, args.root)
    elif args.cmd == "structure-prompt":
        structure_prompt(args.case, args.stage, args.root)
    elif args.cmd == "structure-import":
        structure_import(args.case, args.stage, args.json, args.root)


if __name__ == "__main__":
    main()
