"""
KhataAI — Week 4 | Phase 4 — Monthly Digest Message
Owner: Aaima

Builds the Urdu monthly summary sent to every active seller
on the 1st of each month.

This file owns:
  - Querying the previous month's totals from the ledger
  - Querying the unpaid debtor list
  - Formatting everything into a clean, readable Urdu message

Younas owns the trigger (when it fires and who it goes to).
Aaima owns the content (what the message says).
"""

import logging
from datetime import datetime, date
from calendar import monthrange
from app.supabase_client import get_supabase

logger = logging.getLogger("khataai.digest_message")

# Urdu month names — used in the digest heading
URDU_MONTHS = {
    1:  "January",  2:  "February", 3:  "March",
    4:  "April",    5:  "May",      6:  "June",
    7:  "July",     8:  "August",   9:  "September",
    10: "October",  11: "November", 12: "December",
}


def _get_previous_month() -> tuple[int, int]:
    """Returns (year, month) for the previous calendar month."""
    today = date.today()
    if today.month == 1:
        return today.year - 1, 12
    return today.year, today.month - 1


def _get_month_totals(user_id: str, year: int, month: int) -> tuple[float, float]:
    """Gets total income and expense for a given month from ledger_entries."""
    supabase = get_supabase()
    start    = f"{year}-{month:02d}-01"
    _, last_day = monthrange(year, month)
    end      = f"{year}-{month:02d}-{last_day}"

    try:
        result = (
            supabase.table("ledger_entries")
            .select("amount, type")
            .eq("user_id", user_id)
            .gte("date", start)
            .lte("date", end)
            .execute()
        )
        income  = sum(r["amount"] for r in result.data if r["type"] == "income")
        expense = sum(r["amount"] for r in result.data if r["type"] == "expense")
        return float(income), float(expense)
    except Exception as e:
        logger.error("Digest totals query failed for %s: %s", user_id, e)
        return 0.0, 0.0


def _get_unpaid_debtors(user_id: str) -> list[dict]:
    """Gets all unpaid entries for the user."""
    supabase = get_supabase()
    try:
        result = (
            supabase.table("ledger_entries")
            .select("vendor, amount")
            .eq("user_id", user_id)
            .eq("is_paid", False)
            .execute()
        )
        return result.data or []
    except Exception as e:
        logger.error("Digest debtors query failed for %s: %s", user_id, e)
        return []


def build_digest_message(user_id: str) -> str:
    """
    Phase 4 — Aaima.

    Builds the full monthly Urdu digest for one user.
    Called by Younas's digest_trigger.py.

    Example output:
        KhataAI — June ka Hisaab

        Kamaya:  Rs. 45,000
        Kharch:  Rs. 12,500
        Net:     Rs. 32,500

        Hisaab mein 2 log hain:
        1. Sana — Rs. 2,500
        2. Karim Fabrics — Rs. 8,000

        Bohat acha mahina raha! Allah aapke rizq mein barkat de. Ameen.
    """
    year, month = _get_previous_month()
    month_name  = URDU_MONTHS[month]

    income, expense = _get_month_totals(user_id, year, month)
    net             = income - expense
    debtors         = _get_unpaid_debtors(user_id)

    # ── Build message ────────────────────────────────────────────────────────
    lines = [
        f"KhataAI — {month_name} ka Hisaab 📊",
        "",
        f"Kamaya:  Rs. {income:,.0f}",
        f"Kharch:  Rs. {expense:,.0f}",
        f"Net:     Rs. {net:,.0f}",
    ]

    # Debtor section
    if debtors:
        lines.append("")
        lines.append(f"Hisaab mein {len(debtors)} log hain:")
        for i, d in enumerate(debtors, start=1):
            vendor = d.get("vendor") or "Unknown"
            amount = d.get("amount", 0)
            lines.append(f"{i}. {vendor} — Rs. {amount:,.0f}")
    else:
        lines.append("")
        lines.append("Sab ne payment kar di! Masha Allah. 🎉")

    # Closing encouragement
    lines.append("")
    if net > 0:
        lines.append("Bohat acha mahina raha! Allah aapke rizq mein barkat de. Ameen. 🤲")
    elif net == 0:
        lines.append("Is baar income aur kharch barabar rahe. Agla mahina aur behtar hoga! 💪")
    else:
        lines.append("Is mahine thoda mushkil raha — lekin mehnat rang laye gi. Himmat rakhein! 💪")

    return "\n".join(lines)
