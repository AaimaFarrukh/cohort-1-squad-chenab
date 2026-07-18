"""
KhataAI — Week 4 | Phase 4 — Digest Trigger
Owner: Younas

Two ways to fire the monthly digest:

1. AUTOMATIC — pg_cron fires on the 1st of every month at 9am PKT (4am UTC).
   Calls POST /internal/run-digest on Railway.
   The cron schedule is defined in Aaima's schema.sql (Week 4 addition).

2. MANUAL — seller types "digest" in WhatsApp.
   Fires immediately for that one user.
   Used for testing without waiting for the 1st of the month.

Younas owns: the trigger endpoint + the scheduler loop.
Aaima owns: digest_message() — the actual Urdu message content.
"""

import os
import logging
from app.supabase_client import get_supabase
from app.whatsapp import send_text
from app.digest_message import build_digest_message  # Aaima

logger = logging.getLogger("khataai.digest_trigger")

CRON_SECRET = os.environ.get("CRON_SECRET", "")


async def fire_digest_for_user(user_id: str, phone_number: str) -> bool:
    """
    Phase 4 — Younas.

    Fires the monthly digest for a single user.
    Called by both the manual trigger (seller types "digest")
    and the automated cron loop.

    Returns True if digest was sent, False on failure.
    """
    try:
        message = build_digest_message(user_id)   # Aaima builds the content
        await send_text(phone_number, message)
        logger.info("Digest sent to %s", phone_number)
        return True
    except Exception as e:
        logger.error("Digest failed for user %s: %s", user_id, e)
        return False


async def run_digest_for_all_active_users() -> int:
    """
    Phase 4 — Younas.

    Loops through all active users who have had at least one ledger
    entry in the past 30 days and fires the digest for each.

    Called by POST /internal/run-digest (triggered by pg_cron).
    Returns the number of digests successfully sent.
    """
    supabase = get_supabase()

    # Find active users with recent activity
    # "recent" = at least one ledger entry in the past 30 days
    try:
        result = supabase.rpc("get_active_users_for_digest").execute()
        users  = result.data or []
    except Exception as e:
        logger.error("Failed to fetch active users for digest: %s", e)
        return 0

    sent = 0
    for user in users:
        success = await fire_digest_for_user(user["id"], user["phone_number"])
        if success:
            sent += 1

    logger.info("Monthly digest complete: %d sent out of %d users", sent, len(users))
    return sent


def verify_cron_secret(secret: str | None) -> bool:
    """
    Validates the X-Cron-Secret header on /internal/run-digest.
    Prevents anyone from triggering the digest endpoint externally.
    """
    if not CRON_SECRET:
        logger.warning("CRON_SECRET not set — digest endpoint is unprotected")
        return True   # Allow during local dev when secret is not configured
    return secret == CRON_SECRET
