"""Provider-agnostic LLM access. Anthropic, OpenAI, DeepSeek, or any OpenAI-compatible endpoint.

The product must not lock users to one vendor. This module auto-detects whichever key is
present and routes to the right API. The rest of the pipeline calls `call()` / `call_json()`
without knowing or caring which provider answered. Reproducibility is preserved by logging
exactly which provider+model was used.

Selection order (first match wins), override with EPISTEMIC_PROVIDER:
  ANTHROPIC_API_KEY  -> anthropic   (default model claude-sonnet-4-6)
  OPENAI_API_KEY     -> openai      (default model gpt-4o)
  DEEPSEEK_API_KEY   -> deepseek    (default model deepseek-chat)
  OPENAI_COMPAT_*    -> any OpenAI-compatible endpoint (Groq, Together, Mistral, Ollama, ...)

Per-provider model override: ANTHROPIC_MODEL / OPENAI_MODEL / DEEPSEEK_MODEL / OPENAI_COMPAT_MODEL.
OpenAI-compatible base URL: OPENAI_COMPAT_BASE_URL (e.g. https://api.groq.com/openai/v1).

No key anywhere? Use the dry-run path (src.dryrun) instead. It needs no key.
"""
import json
import os
import re
import sys
import time

DEFAULTS = {
    "anthropic": "claude-sonnet-4-6",
    "openai": "gpt-4o",
    "deepseek": "deepseek-chat",
    "openai_compat": "llama-3.3-70b-versatile",
}


def _detect_provider():
    forced = os.environ.get("EPISTEMIC_PROVIDER", "").strip().lower()
    if forced:
        return forced
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic"
    if os.environ.get("OPENAI_API_KEY"):
        return "openai"
    if os.environ.get("DEEPSEEK_API_KEY"):
        return "deepseek"
    if os.environ.get("OPENAI_COMPAT_API_KEY"):
        return "openai_compat"
    return None


def provider_info():
    """Return (provider, model) without making a call, for logging/reproducibility."""
    p = _detect_provider()
    if not p:
        return (None, None)
    model_env = {
        "anthropic": "ANTHROPIC_MODEL", "openai": "OPENAI_MODEL",
        "deepseek": "DEEPSEEK_MODEL", "openai_compat": "OPENAI_COMPAT_MODEL",
    }[p]
    return (p, os.environ.get(model_env, DEFAULTS[p]))


def _no_key_exit():
    sys.exit(
        "No LLM API key found. Set one of ANTHROPIC_API_KEY / OPENAI_API_KEY / "
        "DEEPSEEK_API_KEY / OPENAI_COMPAT_API_KEY,\n"
        "or use the keyless dry-run path:  python -m src.dryrun prompt ..."
    )


# Free/shared endpoints rate-limit aggressively. Without retry a 429 loses that chunk's
# claims silently, which is worse than waiting — so back off and retry transient failures.
_MAX_ATTEMPTS = 5
_BASE_DELAY = 5.0


def _is_transient(err: str) -> bool:
    e = err.lower()
    return ("429" in e or "rate" in e or "overloaded" in e or "timeout" in e
            or "timed out" in e or "502" in e or "503" in e or "529" in e)


def call(system: str, user: str, max_tokens: int = 8000) -> str:
    """Single model call across whichever provider is configured. Returns raw text.

    Retries rate-limit/transient errors with exponential backoff; a permanent error
    (bad key, no credit, bad model) raises immediately so the run fails loudly."""
    provider, model = provider_info()
    if not provider:
        _no_key_exit()
    for attempt in range(_MAX_ATTEMPTS):
        try:
            if provider == "anthropic":
                return _call_anthropic(model, system, user, max_tokens)
            return _call_openai_like(provider, model, system, user, max_tokens)
        except Exception as e:
            if not _is_transient(str(e)) or attempt == _MAX_ATTEMPTS - 1:
                raise
            delay = _BASE_DELAY * (2 ** attempt)
            print(f"    [retry {attempt + 1}/{_MAX_ATTEMPTS - 1}] transient error; "
                  f"waiting {delay:.0f}s then retrying...")
            time.sleep(delay)


def _call_anthropic(model, system, user, max_tokens):
    try:
        from anthropic import Anthropic
    except ImportError:
        sys.exit("pip install anthropic --break-system-packages")
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        _no_key_exit()
    client = Anthropic(api_key=key)
    resp = client.messages.create(
        model=model, max_tokens=max_tokens, system=system,
        messages=[{"role": "user", "content": user}],
    )
    return "".join(b.text for b in resp.content if b.type == "text")


def _call_openai_like(provider, model, system, user, max_tokens):
    """OpenAI, DeepSeek, and any OpenAI-compatible endpoint share this code path."""
    try:
        from openai import OpenAI
    except ImportError:
        sys.exit("pip install openai --break-system-packages")
    if provider == "openai":
        key = os.environ.get("OPENAI_API_KEY")
        base_url = os.environ.get("OPENAI_BASE_URL")
    elif provider == "deepseek":
        key = os.environ.get("DEEPSEEK_API_KEY")
        base_url = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    else:
        key = os.environ.get("OPENAI_COMPAT_API_KEY")
        base_url = os.environ.get("OPENAI_COMPAT_BASE_URL")
        if not base_url:
            sys.exit("Set OPENAI_COMPAT_BASE_URL (e.g. https://api.groq.com/openai/v1).")
    if not key:
        _no_key_exit()
    client = OpenAI(api_key=key, base_url=base_url) if base_url else OpenAI(api_key=key)
    resp = client.chat.completions.create(
        model=model, max_tokens=max_tokens,
        messages=[{"role": "system", "content": system},
                  {"role": "user", "content": user}],
    )
    return resp.choices[0].message.content or ""


def call_json(system: str, user: str, max_tokens: int = 8000):
    """Model call that must return JSON. Strips fences/preamble, parses, raises on failure."""
    raw = call(system, user, max_tokens)
    return _parse_json(raw)


def _parse_json(raw: str):
    """Robustly pull the first complete JSON value out of a model response.

    Uses json.raw_decode from the first '[' or '{', which parses exactly one value and ignores
    any trailing prose the model appended (the old greedy regex choked on that with 'Extra data').
    Tries each candidate start so a stray bracket in preamble doesn't derail parsing."""
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.MULTILINE).strip()
    decoder = json.JSONDecoder()
    for i, ch in enumerate(cleaned):
        if ch in "[{":
            try:
                value, _ = decoder.raw_decode(cleaned[i:])
                return value
            except json.JSONDecodeError:
                continue
    raise ValueError(f"No JSON found in model output:\n{raw[:500]}")
