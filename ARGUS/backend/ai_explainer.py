"""
Calls Gemini to turn the risk engine's deterministic output into a short,
human-readable explanation. Per the spec: the AI interprets an
already-computed result — it does not calculate risk itself, and it never
sees raw sensor streams, only the compact payload built in main.py.

Uses Gemini specifically because it has a genuine free tier via Google AI
Studio (no credit card required) — see https://aistudio.google.com/apikey.
Free-tier model availability and rate limits do shift over time and by
account/region, so if MODEL below starts erroring or billing unexpectedly,
check https://aistudio.google.com/rate-limit for your project's current
free-tier model list and swap MODEL to whatever's listed there.
"""
import json
import os

from google import genai
from pydantic import BaseModel

MODEL = "gemini-3.1-flash-lite"  # confirmed free-tier as of testing this — see note above if that changes
_client = None  # lazily created — a missing API key shouldn't crash the whole backend at import time


class AIExplanationResult(BaseModel):
    summary: str
    key_evidence: list[str]
    recommended_action: str


def _get_client():
    global _client
    if _client is None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is not set")
        _client = genai.Client(api_key=api_key)
    return _client


PROMPT_PREFIX = """You are ARGUS, a disaster-monitoring assistant. You are given \
a compact, already-computed risk assessment for one sensor node — not raw \
sensor data. Explain it in plain language for an emergency-response operator.

You do not calculate risk, invent numbers, or add evidence that wasn't given \
to you. Only interpret and explain the numbers you're given.

Risk assessment data:
"""


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
    interaction = _get_client().interactions.create(
        model=MODEL,
        input=PROMPT_PREFIX + json.dumps(payload),
        response_format={
            "type": "text",
            "mime_type": "application/json",
            "schema": AIExplanationResult.model_json_schema(),
        },
    )
    parsed = json.loads(interaction.output_text)
    if not all(k in parsed for k in ("summary", "key_evidence", "recommended_action")):
        raise ValueError(f"AI response missing required keys: {parsed}")
    return parsed
