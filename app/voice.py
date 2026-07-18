"""
KhataAI — Week 4 | Phase 3 — Voice Note Support
Owner: Younas

Pakistani sellers use voice notes constantly — faster than typing Urdu.
A seller who would never type a receipt will send a 10-second voice note.

Flow:
  WhatsApp audio message
    -> download bytes from Meta CDN (same as image flow)
    -> send to Gemini 1.5 Flash (handles audio natively)
    -> Gemini transcribes + classifies intent in ONE call
    -> route to existing handlers — no new handlers needed

Why one call:
  - Lower latency (one round trip instead of two)
  - Cheaper (one set of tokens)
  - Gemini can use audio context + text reasoning simultaneously
"""

import os
import json
import logging
from google import genai
from google.genai import types

logger = logging.getLogger("khataai.voice")

_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    return _client


VOICE_PROMPT = (
    "This is a WhatsApp voice note from a Pakistani small business seller. "
    "The seller speaks in Urdu, Roman Urdu, or mixed Urdu/English. "
    "Do the following:\n\n"
    "1. Transcribe the voice note exactly.\n"
    "2. Classify the intent into ONE of:\n"
    "   RECEIPT - seller is recording a payment received or expense paid\n"
    "   EARNINGS_QUERY - seller is asking about their earnings or profit\n"
    "   DEBTOR_QUERY - seller is asking who still owes them money\n"
    "   UNKNOWN - anything else\n\n"
    "3. For RECEIPT intent, extract: amount in PKR (number only), "
    "vendor or customer name, date if mentioned, "
    "whether it is income or expense, "
    "and whether it is udhaar (unpaid/credit).\n\n"
    "Return JSON only. No explanation. No markdown fences. Format:\n"
    '{"intent": "RECEIPT|EARNINGS_QUERY|DEBTOR_QUERY|UNKNOWN", '
    '"transcription": "string", '
    '"receipt": {"amount": number, "vendor": "string", '
    '"type": "income|expense", "date": "YYYY-MM-DD or null", '
    '"is_udhaar": false}}\n\n'
    "For non-RECEIPT intents set receipt to null."
)

VOICE_FAILED_MESSAGE = (
    "Voice note sun nahi paya. 😔\n\n"
    "Kya aap:\n"
    "• Dobara voice note bhejein\n"
    "• Ya text mein likhein\n\n"
    "Shukriya!"
)


def transcribe_and_classify(audio_bytes: bytes, mime_type: str = "audio/ogg") -> dict | None:
    """
    Phase 3 — Younas.

    Sends voice note audio to Gemini 1.5 Flash and returns a structured dict:
        {intent, transcription, receipt}

    WhatsApp voice notes arrive as audio/ogg (Opus codec).
    Gemini 1.5 Flash accepts: ogg, mp4, wav, mp3, aiff, flac, webm.

    Returns None on any failure — caller sends VOICE_FAILED_MESSAGE.
    """
    try:
        client   = _get_client()
        response = client.models.generate_content(
            model=os.environ.get("GEMINI_MODEL", "gemini-1.5-flash"),
            contents=[
                types.Part.from_bytes(data=audio_bytes, mime_type=mime_type),
                VOICE_PROMPT,
            ],
        )

        raw = response.text.strip()
        # Strip markdown fences defensively
        if raw.startswith("```"):
            raw = raw.strip("`").replace("json\n", "", 1).replace("json", "", 1).strip()

        data = json.loads(raw)

        if "intent" not in data:
            logger.warning("Gemini voice response missing intent: %s", data)
            return None

        return data

    except json.JSONDecodeError as e:
        logger.error("Gemini voice returned invalid JSON: %s", e)
        return None
    except Exception as e:
        logger.error("Voice transcription failed: %s", e)
        return None
