"""
KhataAI — Week 3 | Beta User Whitelist
Owner: Aaima

This is the FIRST check on every incoming WhatsApp message.
Nothing else — no AI, no DB writes, no ledger — runs until
this check passes.

How to add a new beta user:
  Option 1 (Supabase dashboard):
    Go to Table Editor → beta_users → Insert row → add phone number
  Option 2 (SQL):
    insert into beta_users (phone_number, name, added_by)
    values ('+923001234567', 'Seller Name', 'aaima');

Phone number format: always include country code with +
  Pakistan numbers: +92 followed by 10 digits
  Example: +923001234567
"""

import logging
from app.supabase_client import get_supabase

logger = logging.getLogger("khataai.whitelist")

# The message sent to anyone not on the beta list.
# Clear, polite, and tells them how to get access.
REJECTION_MESSAGE = (
    "Assalam o Alaikum! 👋\n\n"
    "KhataAI abhi sirf invited beta users ke liye available hai.\n\n"
    "Beta access ke liye humse contact karein. Shukriya!"
)


def is_whitelisted(phone_number: str) -> bool:
    """
    Checks if a phone number exists in the beta_users table.

    Returns True  → user is approved, proceed with the message
    Returns False → user is not approved, send REJECTION_MESSAGE

    Fails OPEN on database errors — if we can't check, we let the
    message through rather than blocking legitimate beta users.
    """
    try:
        supabase = get_supabase()
        result = (
            supabase.table("beta_users")
            .select("phone_number")
            .eq("phone_number", phone_number)
            .execute()
        )
        return len(result.data) > 0
    except Exception as e:
        logger.error("Whitelist check failed for %s: %s", phone_number, e)
        # Fail open — a DB error shouldn't block beta users
        return True
