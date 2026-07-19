"""Ingestion stage: sources -> atomic claims with provenance.

Reads cases/<case>/sources.json, fetches/loads each source's text, extracts atomic
claims via the ingest prompt, assigns stable ids, writes cases/<case>/out/claims.json.

Source text loading: this scaffold expects pre-fetched text in cases/<case>/raw/<source_id>.txt
(fetching contested-topic pages is left to the user to control exactly what's ingested —
provenance demands knowing precisely what went in). A helper to fetch is stubbed below.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from prompts.ingest import SYSTEM, USER_TEMPLATE  # noqa: E402
from src.llm import call_json  # noqa: E402


def load_source_text(case_dir: str, source_id: str) -> str:
    path = os.path.join(case_dir, "raw", f"{source_id}.txt")
    if not os.path.exists(path):
        print(f"  [skip] no raw text for '{source_id}' at {path} — add it to ingest this source.")
        return ""
    with open(path, encoding="utf-8") as f:
        return f.read()


def ingest(case: str, root: str = ".", limit_chunks: int = 0) -> dict:
    case_dir = os.path.join(root, "cases", case)
    with open(os.path.join(case_dir, "sources.json"), encoding="utf-8") as f:
        manifest = json.load(f)

    all_claims = []
    counter = 1
    for src in manifest["sources"]:
        content = load_source_text(case_dir, src["id"])
        if not content:
            continue
        # Drop the fetcher's leading "# ..." metadata/caution header before extraction:
        # title/author/side are passed to the model separately via USER_TEMPLATE, so the
        # header is pure scaffolding. Only the leading block is stripped; a '#' that appears
        # inside the article body is left intact.
        _lines = content.splitlines()
        _i = 0
        while _i < len(_lines) and (_lines[_i].startswith("#") or not _lines[_i].strip()):
            _i += 1
        content = "\n".join(_lines[_i:]).strip()
        if not content:
            continue
        print(f"  ingesting {src['id']} ({len(content)} chars)...")
        # chunk long sources to stay within limits; simple paragraph chunking
        chunks = _chunk(content, 12000)
        if limit_chunks and len(chunks) > limit_chunks:
            print(f"    [smoke test] limiting to first {limit_chunks} of {len(chunks)} chunks")
            chunks = chunks[:limit_chunks]
        for chunk in chunks:
            user = USER_TEMPLATE.format(
                title=src["title"], author=src.get("author", "unknown"),
                side=src.get("side", "n/a"), content=chunk,
            )
            try:
                claims = _as_claim_list(call_json(SYSTEM, user, max_tokens=16000))
            except Exception as e:
                print(f"    [warn] extraction failed on a chunk: {e}")
                continue
            for c in claims:
                if not isinstance(c, dict):
                    continue  # skip stray non-object entries the model may emit
                c_id = f"C{counter:03d}"
                counter += 1
                all_claims.append({
                    "id": c_id,
                    "text": c.get("text", ""),
                    "kind": c.get("kind", "evidence"),
                    "attestations": [{
                        "source_id": src["id"],
                        "verbatim_span": c.get("verbatim_span", ""),
                        "context": c.get("context", ""),
                        "framing": c.get("framing", ""),
                    }],
                    "probability_estimates": (
                        [{"source_id": src["id"], "value": c["probability_estimate"], "note": ""}]
                        if c.get("probability_estimate") else []
                    ),
                })

    out_dir = os.path.join(case_dir, "out")
    os.makedirs(out_dir, exist_ok=True)
    out = {"case": case, "sources": manifest["sources"], "claims": all_claims}
    with open(os.path.join(out_dir, "claims.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(f"  -> {len(all_claims)} claims written to {out_dir}/claims.json")
    return out


def _as_claim_list(obj):
    """The extraction prompt asks for a bare JSON array, but a model may validly wrap it in an
    object ({"claims": [...]}) or return a single claim. Normalize all of these to a list of
    claim dicts so one phrasing choice can't crash the run."""
    if isinstance(obj, list):
        return obj
    if isinstance(obj, dict):
        for key in ("claims", "items", "results", "data", "atomic_claims"):
            if isinstance(obj.get(key), list):
                return obj[key]
        if obj.get("text") or obj.get("verbatim_span"):
            return [obj]  # a single claim object
        for v in obj.values():  # fall back to the first list-valued field
            if isinstance(v, list):
                return v
    return []


def _chunk(text: str, size: int):
    # Normalize line endings first: Windows files use \r\n, so paragraph breaks are
    # \r\n\r\n which contain no "\n\n" — splitting on "\n\n" would yield one giant chunk.
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    paras = text.split("\n\n")
    chunks, cur = [], ""
    for p in paras:
        # Hard-split any single paragraph larger than `size` so a source with no blank
        # lines (or one huge paragraph) still gets chunked instead of overflowing.
        while len(p) > size:
            if cur:
                chunks.append(cur)
                cur = ""
            chunks.append(p[:size])
            p = p[size:]
        if len(cur) + len(p) > size and cur:
            chunks.append(cur)
            cur = ""
        cur += p + "\n\n"
    if cur.strip():
        chunks.append(cur)
    return chunks
