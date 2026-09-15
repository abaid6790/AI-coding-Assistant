"""
The code-intelligence features (Phase 8) need structured output from the
AI — severity-tagged findings, quality scores, generated code separated
from explanation — but an LLM's response is still just text. These
helpers parse that text defensively: if the model didn't follow
instructions exactly, callers get a sane fallback instead of a 500.
"""
import json
import re

_JSON_FENCE_RE = re.compile(r"^```(?:json)?\s*\n(.*)\n```$", re.DOTALL)
_ANY_FENCE_RE = re.compile(r"```(?:\w+)?\n(.*?)```", re.DOTALL)


def extract_json(text: str) -> dict:
    """Parse a JSON object out of a model response, tolerating a
    markdown code fence around it (models do this constantly even when
    told not to). Raises ValueError with the original text attached if
    it still isn't valid JSON, so callers can fall back gracefully."""
    stripped = text.strip()
    fence_match = _JSON_FENCE_RE.match(stripped)
    candidate = fence_match.group(1) if fence_match else stripped
    try:
        return json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Model response was not valid JSON: {exc}") from exc


def extract_code_block(text: str) -> str:
    """Pull the first fenced code block out of a response; if there
    isn't one, return the whole response trimmed. Used for
    tests/documentation output where we want just the code, not any
    surrounding prose the model added despite instructions not to."""
    match = _ANY_FENCE_RE.search(text)
    if match:
        return match.group(1).rstrip("\n")
    return text.strip()


def truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n… (truncated, {len(text) - limit} more characters)"
