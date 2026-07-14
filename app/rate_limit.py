"""
KhataAI — Week 3 | API Rate Limiting
Owner: Younas

Prevents a single beta user from draining Gemini API credits.

How it works:
  - Each user gets DAILY_LIMIT receipt scans per day
  - Counter stored in the users table (daily_message_count column — Aaima's schema)
  - Counter resets at midnight UTC via pg_cron (defined in Aaima's schema.sql)
  - Check runs AFTER whitelist, BEFORE any AI call

Why this matters:
  - Gemini 1.5 Flash free tier: 1,500 requests/day total across all users
  - Without a limit, one user sending 1,500 receipts blocks everyone else
  - At 20 receipts/day per user, 75 beta users can use the service simultaneously
"""

import os
import logging
from app.supabase_client import get_supabase

logger = logging.getLogger("khataai.rate_limit")

# Configurable via env var — default 20 receipts/day for beta
DAILY_LIMIT = int(os.environ.get("DAILY_RECEIPT_LIMIT", 20))

LIMIT_REACHED_MESSAGE = (
    f"Aap ne aaj ki limit ({DAILY_LIMIT} receipts) use kar li. "
    "Kal subah reset ho jaye gi. Shukriya! 🙏"
)


def is_within_daily_limit(phone_number: str) -> bool:
    """
    Returns True if the user has NOT yet hit their daily receipt cap.
    Returns False if they have — caller sends LIMIT_REACHED_MESSAGE.

    Uses phone_number (not user_id) so this can run before get_or_create_user.
    """
    try:
        supabase = get_supabase()
        result = (
            supabase.table("users")
            .select("daily_message_count")
            .eq("phone_number", phone_number)
            .execute()
        )
        if not result.data:
            # User not in DB yet — they haven't used anything, so within limit
            return True
        count = result.data[0].get("daily_message_count", 0) or 0
        return count < DAILY_LIMIT
    except Exception as e:
        logger.error("Rate limit check failed for %s: %s", phone_number, e)
        # Fail open — if the check errors, don't block the user
        return True


def increment_daily_count(phone_number: str) -> None:
    """
    Increments the user's daily receipt counter by 1.
    Called AFTER a receipt is successfully processed — not before.

    Uses a Postgres RPC function (defined in schema.sql) for atomic increment,
    so two concurrent receipts from the same user don't race each other.
    """
    try:
        supabase = get_supabase()
        supabase.rpc(
            "increment_daily_count",
            {"target_phone": phone_number},
        ).execute()
    except Exception as e:
        logger.error("Failed to increment daily count for %s: %s", phone_number, e)
        # Non-fatal — receipt is already saved, don't fail the whole request
