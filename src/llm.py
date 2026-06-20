"""Thin wrapper around the Anthropic Messages API with robust JSON extraction.

Keeps the model call in one place so every stage is reproducible: same model string,
same parsing, logged. No hand-tuned post-processing of content — the prompt does the work.
"""
import json
import os
import re
import sys

try:
    from anthropic import Anthropic
except ImportError:
    Anthropic = None

MODEL = "claude-sonnet-4-6"  # pin for reproducibility; bump deliberately


def _client():
    if Anthropic is None:
        sys.exit("anthropic package not installed. Run: pip install anthropic --break-system-packages")
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        sys.exit("Set ANTHROPIC_API_KEY in your environment.")
    return Anthropic(api_key=key)


def call(system: str, user: str, max_tokens: int = 8000) -> str:
    """Single model call, returns raw text."""
    resp = _client().messages.create(
        model=MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return "".join(block.text for block in resp.content if block.type == "text")


def call_json(system: str, user: str, max_tokens: int = 8000):
    """Model call that must return JSON. Strips fences, parses, raises on failure."""
    raw = call(system, user, max_tokens)
    cleaned = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()
    # find the outermost JSON array or object
    match = re.search(r"(\[.*\]|\{.*\})", cleaned, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON found in model output:\n{raw[:500]}")
    return json.loads(match.group(1))
