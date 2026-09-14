"""Thin shared wrapper around the Claude API so every agent calls it the same way."""
import json

import config

_client = None


def _get_client():
    global _client
    if _client is None:
        import anthropic
        _client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    return _client


def ask_claude(system: str, user: str, max_tokens: int = 600) -> str:
    """Single-turn call. Returns plain text. Raises if ANTHROPIC_API_KEY is unset -
    callers should check config.HAS_CLAUDE before calling."""
    client = _get_client()
    resp = client.messages.create(
        model=config.CLAUDE_MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return resp.content[0].text.strip()


def ask_claude_json(system: str, user: str, max_tokens: int = 600) -> dict:
    """Same as ask_claude but instructs the model to return JSON and parses it."""
    text = ask_claude(
        system=system + "\n\nRespond with ONLY valid JSON, no markdown fences, no commentary.",
        user=user,
        max_tokens=max_tokens,
    )
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text)
