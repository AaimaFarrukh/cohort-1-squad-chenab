"""
KhataAI — Week 4 | Phase 3 — Debtor Query
Owner: Aaima

Handles "kaun hisaab mein hai?" — returns a clean Urdu list
of sellers who still owe money (is_paid = false).

Design decisions:
  - No calculations needed — just a list
  - Plain Urdu, no formatting characters or markdown
  - If nobody owes — say so clearly and positively
  - Show vendor name + amount only — no dates, no extra info
"""

import logging
from app.supabase_client import get_supabase

logger = logging.getLogger("khataai.debtor")

# Message when debtor list is empty — good news!
ALL_CLEAR_MESSAGE = (
    "Masha Allah! Abhi koi hisaab mein nahi hai. "
    "Sab ne payment kar di hai. Shukriya! 🎉"
)

# Prefix shown before the debtor list
DEBTOR_LIST_HEADER = "Yeh log abhi hisaab mein hain:\n\n"

# Suffix shown after the debtor list
DEBTOR_LIST_FOOTER = "\nKisi ko reminder bhejna ho toh mujhe batayein."


def get_unpaid_entries(user_id: str) -> list[dict]:
    """
    Queries ledger_entries for all unpaid invoices (is_paid = false)
    for this user.

    Returns a list of dicts with vendor and amount.
    Empty list if no unpaid entries.
    """
    try:
        supabase = get_supabase()
        result = (
            supabase.table("ledger_entries")
            .select("vendor, amount, date")
            .eq("user_id", user_id)
            .eq("is_paid", False)
            .order("date", desc=False)
            .execute()
        )
        return result.data or []
    except Exception as e:
        logger.error("get_unpaid_entries failed for user %s: %s", user_id, e)
        return []


def handle_debtor_query(user_id: str) -> str:
    """
    Phase 3 — Aaima.

    Builds the Urdu debtor list message for a user.
    Called from main.py when intent is DEBTOR_QUERY.

    Examples:
      No debtors:
        "Masha Allah! Abhi koi hisaab mein nahi hai..."

      With debtors:
        "Yeh log abhi hisaab mein hain:
         1. Sana — Rs. 2,500
         2. Karim Fabrics — Rs. 8,000
         3. Raheela — Rs. 1,200
         Kisi ko reminder bhejna ho toh mujhe batayein."
    """
    entries = get_unpaid_entries(user_id)

    if not entries:
        return ALL_CLEAR_MESSAGE

    lines = []
    for i, entry in enumerate(entries, start=1):
        vendor = entry.get("vendor") or "Unknown"
        amount = entry.get("amount", 0)
        lines.append(f"{i}. {vendor} — Rs. {amount:,.0f}")

    return DEBTOR_LIST_HEADER + "\n".join(lines) + DEBTOR_LIST_FOOTER
