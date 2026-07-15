"""
KhataAI — Week 3 | Ledger Writer + Urdu Messages
Owner: Aaima

Handles:
  - Writing extracted receipt data to the ledger_entries table
  - All Urdu confirmation and error messages the seller sees
  - Debtor (udhaar) detection from WhatsApp image captions

Every message the seller receives is written here.
If the Urdu wording needs changing, this is the only file to edit.
"""

import logging
from datetime import date
from app.supabase_client import get_supabase

logger = logging.getLogger("khataai.ledger")

# ── Urdu messages — all in one place for easy editing ────────────────────

# Sent when Gemini can't read the receipt
FAILED_OCR_MESSAGE = (
    "Maafi chahiye, yeh receipt samajh nahi aaya. 😔\n\n"
    "Kya aap:\n"
    "• Thodi roshan jagah mein dobara photo len\n"
    "• Ya WhatsApp invoice screenshot bhejein\n\n"
    "Shukriya!"
)

# Sent when an image download or network error occurs
NETWORK_ERROR_MESSAGE = (
    "Receipt download nahi ho saki. Kya aap dobara bhej sakte hain?"
)

# Keywords that flag a receipt as unpaid (udhaar)
# If the seller includes any of these in the image caption,
# the entry is saved with is_paid = False and shows in the debtor list.
UNPAID_KEYWORDS = ["udhaar", "baqaya", "unpaid", "credit pe", "baad mein"]


def determine_is_paid(caption: str | None) -> bool:
    """
    Reads the WhatsApp image caption to decide if this is an unpaid invoice.

    Usage: seller types "udhaar" in the caption when forwarding a receipt
    for money they haven't collected yet.

    Returns True  = paid (default)
    Returns False = unpaid / udhaar
    """
    if not caption:
        return True
    lowered = caption.strip().lower()
    return not any(kw in lowered for kw in UNPAID_KEYWORDS)


def save_ledger_entry(
    user_id: str,
    extracted: dict,
    image_url: str,
    raw_text: str,
    caption: str | None = None,
) -> dict:
    """
    Phase 2 — Aaima.

    Inserts one row into ledger_entries from Gemini's extracted receipt data.

    extracted dict format (from Younas's gemini_client.py):
        {date, amount, vendor, type}

    Returns the saved row dict (used by confirmation_message to build the reply).
    """
    is_paid = determine_is_paid(caption)

    row = {
        "user_id":   user_id,
        "date":      extracted.get("date") or str(date.today()),
        "amount":    extracted["amount"],
        "vendor":    extracted.get("vendor") or "Unknown",
        "type":      extracted["type"],
        "image_url": image_url,
        "raw_text":  raw_text,
        "is_paid":   is_paid,
    }

    try:
        supabase = get_supabase()
        result   = supabase.table("ledger_entries").insert(row).execute()
        return result.data[0]
    except Exception as e:
        logger.error("Failed to save ledger entry: %s | row: %s", e, row)
        raise


def confirmation_message(entry: dict) -> str:
    """
    Phase 2 — Aaima.

    Builds the Urdu confirmation message sent to the seller after a
    receipt is successfully saved.

    Examples:
      "Receipt save ho gayi: Rs. 1,200 Karim Fabrics ✓"
      "Receipt save ho gayi: Rs. 3,500 Sana ✓ (Udhaar mein add ho gaya)"
    """
    amount = entry.get("amount", "?")
    vendor = entry.get("vendor", "Unknown")
    is_paid = entry.get("is_paid", True)

    base = f"Receipt save ho gayi: Rs. {amount} {vendor} ✓"

    if not is_paid:
        base += "\n(Udhaar mein add ho gaya 📋)"

    return base
