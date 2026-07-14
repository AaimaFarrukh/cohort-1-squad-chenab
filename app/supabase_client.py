"""
KhataAI — Week 3 | Supabase Client
Owner: Younas

Lazy singleton Supabase client + receipt image upload helper.
Shared by both Younas and Aaima's code — imported from both sides.
"""

import os
import logging
from supabase import create_client, Client

logger = logging.getLogger("khataai.supabase")

_supabase: Client | None = None

RECEIPTS_BUCKET     = os.environ.get("SUPABASE_STORAGE_BUCKET", "receipts")
# 10-year signed URL — pragmatic choice since we have no "view receipt" UI yet
SIGNED_URL_TTL      = 60 * 60 * 24 * 365 * 10


def get_supabase() -> Client:
    """Lazy singleton — one connection reused across all requests."""
    global _supabase
    if _supabase is None:
        _supabase = create_client(
            os.environ["SUPABASE_URL"],
            os.environ["SUPABASE_SERVICE_ROLE_KEY"],
        )
    return _supabase


def upload_receipt_image(user_id: str, filename: str, data: bytes, mime_type: str) -> str | None:
    """
    Phase 2 — Younas.

    Uploads a receipt image to Supabase Storage and returns a long-lived
    signed URL. The path is user_id/filename so each user's receipts are
    stored in their own folder.

    Returns None on failure — caller falls back to the temporary Meta CDN URL
    so the receipt is still logged rather than lost entirely.
    """
    supabase = get_supabase()
    path = f"{user_id}/{filename}"

    try:
        supabase.storage.from_(RECEIPTS_BUCKET).upload(
            path, data, {"content-type": mime_type}
        )
    except Exception as e:
        logger.error("Receipt image upload failed: %s", e)
        return None

    try:
        signed = supabase.storage.from_(RECEIPTS_BUCKET).create_signed_url(
            path, SIGNED_URL_TTL
        )
        return signed.get("signedURL") or signed.get("signedUrl")
    except Exception as e:
        logger.error("Uploaded receipt but failed to sign URL: %s", e)
        # Object exists in storage, just return the path as fallback
        return path
