"""Fetch source texts for a case into cases/<case>/raw/<source_id>.txt

No API key needed — this just downloads and cleans web pages so the pipeline has
local, controlled copies of each source (provenance demands knowing exactly what went in).

    python -m src.fetch --case covid
    python -m src.fetch --case covid --only acx_writeup
    python -m src.fetch --case covid --list          # show what's in the manifest

Some sources (paywalled, JS-heavy, or video) can't be auto-fetched. For those the script
writes a small placeholder .txt telling you to paste the text manually, and reports them
at the end so you know exactly what needs a hand.
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.request
import urllib.error

UA = "Mozilla/5.0 (compatible; epistemic-stack/1.0; research)"
# Some sites reject requests that omit Accept headers (urllib sends none by default), even
# when the User-Agent is fine — so we send the same headers a browser/curl would. Not spoofing
# a browser (UA stays honest); just not tripping bot-filters that key on missing Accept.
_HEADERS = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def _strip_html(html: str) -> str:
    """Lightweight HTML -> text. Good enough for article prose; not a full parser."""
    # drop script/style/head
    html = re.sub(r"(?is)<(script|style|head|nav|footer|svg).*?</\1>", " ", html)
    # turn block tags into newlines so paragraphs survive
    html = re.sub(r"(?i)</(p|div|h[1-6]|li|br|tr)\s*>", "\n", html)
    html = re.sub(r"(?i)<br\s*/?>", "\n", html)
    # remove all remaining tags
    text = re.sub(r"(?s)<[^>]+>", " ", html)
    # unescape the common entities
    for a, b in [("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"), ("&quot;", '"'),
                 ("&#39;", "'"), ("&rsquo;", "\u2019"), ("&lsquo;", "\u2018"),
                 ("&ldquo;", "\u201c"), ("&rdquo;", "\u201d"), ("&nbsp;", " "),
                 ("&mdash;", "\u2014"), ("&ndash;", "\u2013")]:
        text = text.replace(a, b)
    # collapse whitespace, keep paragraph breaks
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)
    lines = [ln.strip() for ln in text.splitlines()]
    return "\n".join(ln for ln in lines if ln)


# Markers that reliably signal the end of the article body and the start of page chrome —
# comment sections, related-post rails, tag/author indexes, blogrolls. These effectively never
# appear inside real article prose, so we cut at the first whole-line occurrence.
_END_MARKERS = re.compile(
    r"^\s*(comments? are closed|leave a (reply|comment)|post a comment"
    r"|related (posts|articles|stories)|you might also like|more stories"
    r"|recent posts|most (read|popular)|top\s+\d+\s+authors|all authors"
    r"|blogroll|post navigation|share this( article| post)?|sign up for our"
    r"|categories)\s*[:.]?\s*$", re.I)


def _is_list_noise(line: str) -> bool:
    """A short, unpunctuated line — the shape of tag clouds, author rosters, and nav lists.
    Sentence-like lines (ending in punctuation) are kept."""
    s = line.strip()
    if not s or len(s) > 40:
        return False
    if s[-1] in ".!?:’”\"'":
        return False
    return len(s.split()) <= 4


def _trim_boilerplate(text: str) -> str:
    """Cut trailing page chrome that HTML-stripping leaves behind (comments, tag clouds,
    author lists, blogrolls). Marker-based cut, then a trailing short-list-line sweep.
    This is a heuristic: a mis-cut trims a little real content, it never mangles the middle —
    so the fetched files should still be eyeballed."""
    lines = text.split("\n")
    for i, ln in enumerate(lines):
        if _END_MARKERS.match(ln):
            lines = lines[:i]
            break
    while lines and _is_list_noise(lines[-1]):
        lines.pop()
    return "\n".join(lines).strip()


def _fetch(url: str, timeout: int = 30) -> str:
    req = urllib.request.Request(url, headers=_HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
        if resp.headers.get("Content-Encoding") == "gzip":
            import gzip
            raw = gzip.decompress(raw)
        charset = resp.headers.get_content_charset() or "utf-8"
        return raw.decode(charset, errors="replace")


def fetch_case(case: str, only: str = None, root: str = "."):
    case_dir = os.path.join(root, "cases", case)
    with open(os.path.join(case_dir, "sources.json"), encoding="utf-8") as f:
        manifest = json.load(f)
    raw_dir = os.path.join(case_dir, "raw")
    os.makedirs(raw_dir, exist_ok=True)

    ok, manual, failed = [], [], []
    for src in manifest["sources"]:
        sid, url = src["id"], src.get("url", "")
        if only and sid != only:
            continue
        out_path = os.path.join(raw_dir, f"{sid}.txt")
        is_video = "youtu" in url or "video" in url
        if not url or is_video:
            _placeholder(out_path, src, "no fetchable URL (video/manual source)")
            manual.append(sid)
            continue
        try:
            print(f"  fetching {sid} <- {url}")
            html = _fetch(url)
            text = _trim_boilerplate(_strip_html(html))
            if len(text) < 500:
                _placeholder(out_path, src, "fetched page too short (likely JS-rendered or blocked)")
                manual.append(sid)
                continue
            header = (f"# SOURCE: {src.get('title','')}\n"
                      f"# AUTHOR: {src.get('author','')}\n"
                      f"# URL: {url}\n"
                      f"# SIDE: {src.get('side','')}\n"
                      f"# Fetched by src.fetch — verify this is the right content before ingesting.\n\n")
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(header + text)
            ok.append(sid)
            time.sleep(1)  # be polite
        except (urllib.error.HTTPError, urllib.error.URLError, Exception) as e:
            print(f"    [warn] {sid} failed: {e}")
            _placeholder(out_path, src, f"auto-fetch failed: {e}")
            failed.append(sid)

    print("\n=== fetch summary ===")
    print(f"  fetched OK ({len(ok)}): {', '.join(ok) or '-'}")
    if manual:
        print(f"  NEEDS MANUAL PASTE ({len(manual)}): {', '.join(manual)}")
    if failed:
        print(f"  FAILED ({len(failed)}): {', '.join(failed)}")
    if manual or failed:
        print("\n  For the above: open the URL, copy the article text, and paste it into")
        print(f"  cases/{case}/raw/<source_id>.txt (replacing the placeholder).")
    print(f"\n  Files in cases/{case}/raw/ are ready for: python -m src.run --case {case}")


def _placeholder(path, src, reason):
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"# PLACEHOLDER — {reason}\n"
                f"# SOURCE: {src.get('title','')}\n"
                f"# URL: {src.get('url','')}\n"
                f"# Paste the article text below this line, then re-run the pipeline.\n\n")


def list_sources(case: str, root: str = "."):
    with open(os.path.join(root, "cases", case, "sources.json"), encoding="utf-8") as f:
        manifest = json.load(f)
    print(f"Sources for '{case}':")
    for s in manifest["sources"]:
        print(f"  {s['id']:20s} {s.get('title','')}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", required=True)
    ap.add_argument("--only", default=None, help="fetch a single source id")
    ap.add_argument("--list", action="store_true", help="list source ids and exit")
    ap.add_argument("--root", default=".")
    args = ap.parse_args()
    if args.list:
        list_sources(args.case, args.root)
        return
    fetch_case(args.case, args.only, args.root)


if __name__ == "__main__":
    main()
