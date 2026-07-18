"""
KhataAI — Week 4 | Phase 3 — Intent Classifier
Owner: Younas

Detects what type of incoming WhatsApp message it is and routes it
to the correct handler.

Design decision: simple keyword matching, no NLP, no ML model.
Reasons:
  1. Fast — keyword check is microseconds, not an API call
  2. Predictable — sellers learn a small vocabulary, it always works
  3. Cheap — zero API cost for routing
  4. Good enough for MVP — we know exactly what sellers ask

Intent hierarchy (checked in order):
  1. image  -> OCR pipeline (Phase 2, Week 3)
  2. audio  -> voice note pipeline (Phase 3, Week 4)
  3. DIGEST -> manual digest trigger (Phase 4, Week 4)
  4. debtor keywords -> debtor query (Phase 3, Week 4)
  5. earnings keywords -> ledger query (Phase 3, Week 4)
  6. anything else -> unknown fallback (Aaima)
"""

from enum import Enum


class Intent(str, Enum):
    IMAGE          = "image"
    VOICE          = "voice"
    EARNINGS_QUERY = "earnings_query"
    DEBTOR_QUERY   = "debtor_query"
    MANUAL_DIGEST  = "manual_digest"
    UNKNOWN        = "unknown"


EARNINGS_KEYWORDS = [
    "kitna kamaya", "kitna aya", "kya hua", "is mahine",
    "pichle mahine", "profit", "kamaya", "income",
    "total", "summary", "hisaab batao", "report",
]

DEBTOR_KEYWORDS = [
    "kaun hisaab", "hisaab mein hai", "udhaar",
    "baqaya", "kisne nahi diya", "unpaid", "pending", "kaun baqi",
]

DIGEST_TRIGGER = "digest"


def classify(message_type: str, text: str | None) -> Intent:
    """
    Routes an incoming WhatsApp message to the correct Intent.
    """
    if message_type == "image":
        return Intent.IMAGE
    if message_type == "audio":
        return Intent.VOICE

    if not text:
        return Intent.UNKNOWN

    lowered = text.strip().lower()

    if lowered == DIGEST_TRIGGER:
        return Intent.MANUAL_DIGEST
    if any(kw in lowered for kw in DEBTOR_KEYWORDS):
        return Intent.DEBTOR_QUERY
    if any(kw in lowered for kw in EARNINGS_KEYWORDS):
        return Intent.EARNINGS_QUERY

    return Intent.UNKNOWN
