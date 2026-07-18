"""
KhataAI — Week 4 | Phase 3 — Ledger Query Answering
Owner: Younas

Handles earnings queries like "is mahine kitna kamaya?" by:
  1. Querying the ledger for the current month's totals
  2. Passing real numbers to Gemini for a natural Urdu reply

Critical rule: ONLY answer from real ledger data. Never guess, never
estimate, never hallucinate. If there is no data, say so honestly.
"""

import os
import logging
from datetime import datetime
from google import genai
from app.supabase_client import get_supabase

logger = logging.getLogger("khataai.ledger_query")

_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    return _client


def get_month_totals(user_id: str, year: int, month: int) -> tuple[float, float]:
    """
    Queries ledger_entries for a user's income and expense totals
    for the given month.

    Returns: (total_income, total_expense) as floats.
    Both are 0.0 if no entries exist for that month.
    """
    try:
        supabase = get_supabase()

        # Build date range for the month
        start = f"{year}-{month:02d}-01"
        if month == 12:
            end = f"{year + 1}-01-01"
        else:
            end = f"{year}-{month + 1:02d}-01"

        result = (
            supabase.table("ledger_entries")
            .select("amount, type")
            .eq("user_id", user_id)
            .gte("date", start)
            .lt("date", end)
            .execute()
        )

        income  = sum(r["amount"] for r in result.data if r["type"] == "income")
        expense = sum(r["amount"] for r in result.data if r["type"] == "expense")
        return float(income), float(expense)

    except Exception as e:
        logger.error("get_month_totals failed for user %s: %s", user_id, e)
        return 0.0, 0.0


def answer_earnings_query(
    original_question: str,
    income: float,
    expense: float,
    month_name: str,
) -> str:
    """
    Phase 3 — Younas.

    Takes real ledger numbers and uses Gemini to generate a natural,
    conversational Urdu reply to the seller's earnings question.

    Args:
        original_question: What the seller actually typed/said
        income: Total income for the month (from ledger, never guessed)
        expense: Total expense for the month (from ledger, never guessed)
        month_name: e.g. "June", "July"

    The Gemini prompt explicitly forbids hallucination — it may ONLY
    use the numbers provided. This is enforced by the prompt design.
    """
    # If no data at all, return a clear message without calling Gemini
    if income == 0.0 and expense == 0.0:
        return (
            f"{month_name} mein abhi tak koi receipt save nahi hui. "
            "Receipt ki photo bhejein aur main hisaab rakhna shuru kar deta hoon!"
        )

    net = income - expense

    prompt = (
        f"You are KhataAI, a friendly AI bookkeeper for a Pakistani small business seller. "
        f"The seller asked: '{original_question}'\n\n"
        f"Here are the EXACT numbers from their ledger for {month_name}:\n"
        f"  Total income:  Rs. {income:,.0f}\n"
        f"  Total expense: Rs. {expense:,.0f}\n"
        f"  Net profit:    Rs. {net:,.0f}\n\n"
        f"Write a short, warm, conversational reply in Urdu (or Roman Urdu). "
        f"Use ONLY the numbers above — do not add, estimate, or change any figures. "
        f"Keep it to 3-4 lines. End with one line of encouragement. "
        f"Do not use markdown, bold, or bullet points."
    )

    try:
        client   = _get_client()
        response = client.models.generate_content(
            model=os.environ.get("GEMINI_MODEL", "gemini-1.5-flash"),
            contents=[prompt],
        )
        return response.text.strip()
    except Exception as e:
        logger.error("Gemini earnings reply failed: %s", e)
        # Fallback to a plain formatted reply if Gemini fails
        return (
            f"{month_name} ka hisaab:\n"
            f"Aaya: Rs. {income:,.0f}\n"
            f"Kharch: Rs. {expense:,.0f}\n"
            f"Net: Rs. {net:,.0f}"
        )


def handle_earnings_query(user_id: str, question: str) -> str:
    """
    Convenience function called directly from main.py.
    Gets current month totals and returns a Urdu reply.
    """
    now        = datetime.utcnow()
    month_name = now.strftime("%B")  # e.g. "July"
    income, expense = get_month_totals(user_id, now.year, now.month)
    return answer_earnings_query(question, income, expense, month_name)
