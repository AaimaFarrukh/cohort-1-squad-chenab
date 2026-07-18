"""
KhataAI — Week 4 | Phase 3
Ledger Query Answering
Owner: Younas

Handles text questions about monthly earnings and expenses.
Queries the Supabase ledger, calculates totals, passes numbers
to Gemini for a natural Urdu reply.

Critical design rule:
  Only answer from REAL ledger data. Never let Gemini guess or
  invent numbers. Gemini only formats the reply — the numbers
  always come from the database first.
"""

import logging
from datetime import datetime
from app.supabase_client import get_supabase
from app.gemini_client import generate_urdu_reply

logger = logging.getLogger("khataai.earnings")


def get_month_totals(user_id: str, year: int, month: int) -> tuple[float, float]:
    """
    Phase 3 — Younas.

    Queries ledger_entries for a specific user and month.
    Returns (total_income, total_expenses) as floats.

    Both default to 0.0 if there are no entries for that month.
    """
    try:
        supabase   = get_supabase()
        month_str  = f"{year}-{month:02d}"

        # Supabase doesn't have a native month filter, so we use
        # date range: first day to last day of the month
        from calendar import monthrange
        _, last_day = monthrange(year, month)
        start = f"{year}-{month:02d}-01"
        end   = f"{year}-{month:02d}-{last_day}"

        result = (
            supabase.table("ledger_entries")
            .select("amount, type")
            .eq("user_id", user_id)
            .gte("date", start)
            .lte("date", end)
            .execute()
        )

        income   = sum(r["amount"] for r in result.data if r["type"] == "income")
        expenses = sum(r["amount"] for r in result.data if r["type"] == "expense")
        return float(income), float(expenses)

    except Exception as e:
        logger.error("get_month_totals failed for user %s: %s", user_id, e)
        return 0.0, 0.0


def answer_earnings_question(
    user_id: str,
    question: str,
    month_name: str | None = None,
) -> str:
    """
    Phase 3 — Younas.

    Full pipeline for an earnings question:
      1. Get current month totals from Supabase
      2. Pass real numbers to Gemini for natural Urdu formatting
      3. Return the reply string

    Fallback: if Gemini fails, return a plain formatted string directly
    so the seller always gets a response.
    """
    now   = datetime.utcnow()
    year  = now.year
    month = now.month

    if not month_name:
        # Simple month name in Urdu (approximate — sellers will understand)
        urdu_months = {
            1: "January", 2: "February", 3: "March", 4: "April",
            5: "May",     6: "June",     7: "July",  8: "August",
            9: "September", 10: "October", 11: "November", 12: "December"
        }
        month_name = urdu_months.get(month, str(month))

    income, expenses = get_month_totals(user_id, year, month)
    net = income - expenses

    # Build the prompt for Gemini — numbers come from DB, not Gemini
    prompt = (
        f"A Pakistani seller asked: '{question}'\n\n"
        f"Here is the real data from their ledger for {month_name}:\n"
        f"  Total income:   Rs. {income:,.0f}\n"
        f"  Total expenses: Rs. {expenses:,.0f}\n"
        f"  Net profit:     Rs. {net:,.0f}\n\n"
        "Write a friendly, natural reply in Urdu (Roman Urdu is fine). "
        "Include all three numbers. Keep it short — 2 to 3 sentences. "
        "Do NOT add any numbers that are not in the data above. "
        "End with a helpful suggestion like 'Aur kuch poochna ho toh batayein!'"
    )

    try:
        reply = generate_urdu_reply(prompt)
        if reply:
            return reply
    except Exception as e:
        logger.error("Gemini earnings reply failed: %s", e)

    # Fallback — plain Urdu if Gemini fails
    return (
        f"{month_name} mein aapne Rs. {income:,.0f} kamaye "
        f"aur Rs. {expenses:,.0f} kharch kiye. "
        f"Net munafa: Rs. {net:,.0f}. "
        "Aur kuch poochna ho toh batayein! 😊"
    )
