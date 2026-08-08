"""
Calls Claude to turn the risk engine's deterministic output into a short,
human-readable explanation. Per the spec: the AI interprets an
already-computed result — it does not calculate risk itself, and it never
sees raw sensor streams, only the compact payload built in main.py.
"""
import json
import os

import anthropic

MODEL = "claude-haiku-4-5-20251001"  # small structured task — fast/cheap is the right fit here
_client = None  # lazily created — a missing API key shouldn't crash the whole backend at import time


def _get_client():
    global _client
    if _client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set")
        _client = anthropic.Anthropic(api_key=api_key)
    return _client


SYSTEM_PROMPT = """You are ARGUS, a disaster-monitoring assistant. You are given \
a compact, already-computed risk assessment for one sensor node — not raw \
sensor data. Explain it in plain language for an emergency-response operator.

You do not calculate risk, invent numbers, or add evidence that wasn't given \
to you. Only interpret and explain the numbers you're given.

Respond with ONLY a JSON object, no other text, in exactly this shape:
{
  "summary": "one or two sentences, plain language, for an operator",
  "key_evidence": ["short phrase", "short phrase", ...],
  "recommended_action": "one concrete sentence"
}"""


def generate_ai_explanation(payload: dict) -> dict:
    """payload should look like:
    {
      "node": "ARGUS-01", "risk_score": 73, "risk_level": "HIGH",
      "confidence": 0.88, "trend": "INCREASING",
      "temperature_change": "+4.2C / 30min", "humidity_change": "-8% / 30min",
      "distance_change": "-18cm / 30min", "device_health": "HEALTHY",
    }
    Raises on any failure — the caller decides the fallback. This
    deliberately doesn't swallow errors, so a broken API key fails loudly
    rather than silently always returning the same fallback text.
    """
    message = _get_client().messages.create(
        model=MODEL,
        max_tokens=300,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": json.dumps(payload)}],
    )
    text = message.content[0].text.strip()
    # Models occasionally wrap JSON in a code fence despite instructions —
    # strip it defensively rather than fail on an otherwise-good response.
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    parsed = json.loads(text)
    if not all(k in parsed for k in ("summary", "key_evidence", "recommended_action")):
        raise ValueError(f"AI response missing required keys: {parsed}")
    return parsed
