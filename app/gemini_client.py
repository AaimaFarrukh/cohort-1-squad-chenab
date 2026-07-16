"""
KhataAI — Week 3 | Gemini 1.5 Flash OCR
Owner: Younas

Sends receipt images to Gemini and parses the structured JSON response.
This is the core AI call for Phase 2.

Model choice: Gemini 1.5 Flash
  - Cheapest vision model: $0.075 per 1M input tokens
  - One receipt image ≈ $0.001 — well within beta budget
  - Handles Urdu text on receipts natively
  - Fast enough for a conversational WhatsApp response (< 5 seconds)
"""

import os
import json
import logging
from google import genai
from google.genai import types

logger = logging.getLogger("khataai.gemini")

# Lazy singleton — one client instance reused across all requests
_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    return _client


def _model() -> str:
    # Configurable via env so we can swap to Pro for testing
    return os.environ.get("GEMINI_MODEL", "gemini-1.5-flash")


# ---------------------------------------------------------------------------
# The OCR prompt — Younas
#
# Design decisions:
#   1. "Return JSON only" — no prose, no explanation, easier to parse
#   2. "no markdown fences" — Gemini sometimes wraps JSON in ```json blocks
#      despite instructions; we strip them defensively below anyway
#   3. "null for fields that cannot be determined" — safer than hallucinating
#   4. type is strictly "income|expense" — maps directly to our DB check constraint
# ---------------------------------------------------------------------------
OCR_PROMPT = (
    "Extract information from this receipt image. "
    "The receipt may be handwritten, printed, a WhatsApp screenshot, "
    "or an EasyPaisa/JazzCash payment confirmation. "
    "Return JSON only, no explanation, no markdown fences. "
    "Format exactly: "
    '{\"date\": \"YYYY-MM-DD\", \"amount\": number, \"vendor\": \"string\", \"type\": \"income|expense\"}. '
    "Rules: "
    "amount must be a number in PKR (no currency symbol). "
    "type is income if money was received, expense if money was paid out. "
    "If a field cannot be determined, use null. "
    "date must be in YYYY-MM-DD format or null if not visible."
)


def extract_receipt(image_bytes: bytes, mime_type: str = "image/jpeg") -> dict | None:
    """
    Phase 2 — Younas.

    Sends a receipt image to Gemini 1.5 Flash and returns a structured dict:
        {date, amount, vendor, type}

    Returns None if:
      - Gemini returns unparseable output
      - amount or type is missing (minimum required fields)
      - any exception occurs

    The caller is responsible for sending the FAILED_OCR_MESSAGE to the user
    when this returns None.
    """
    try:
        client   = _get_client()
        response = client.models.generate_content(
            model=_model(),
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                OCR_PROMPT,
            ],
        )

        raw = response.text.strip()

        # Gemini sometimes wraps JSON in ```json ... ``` fences despite
        # explicit instructions not to. Strip them defensively.
        if raw.startswith("```"):
            raw = raw.strip("`")
            raw = raw.replace("json\n", "", 1).replace("json", "", 1).strip()

        data = json.loads(raw)

        # amount and type are the minimum we need to save a useful ledger entry.
        if not data.get("amount") or not data.get("type"):
            logger.warning("Gemini returned incomplete receipt data: %s", data)
            return None

        return data

    except json.JSONDecodeError as e:
        logger.error("Gemini OCR returned invalid JSON: %s | raw: %s", e, raw if 'raw' in dir() else "N/A")
        return None
    except Exception as e:
        logger.error("Gemini OCR call failed: %s", e)
        return None
