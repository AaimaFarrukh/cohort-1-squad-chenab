"""
KhataAI — WhatsApp helper (Green API)

Handles all outgoing calls to Green API's WhatsApp instance:
  - Sending text messages back to the seller
  - Downloading media bytes

Green API differs from Meta's Cloud API in one big way: incoming webhooks
already contain the direct downloadUrl for media (image/audio) messages, so
there's no separate "exchange media_id for a URL" step. get_media_url() is
kept only so main.py's existing call sites don't need to change.
"""

import os
import logging
import httpx

logger = logging.getLogger("khataai.whatsapp")

# Green API base URL (same for all instances unless you're on a dedicated server)
GREEN_API_BASE_URL = os.environ.get("GREEN_API_BASE_URL", "https://api.green-api.com")


def _id_instance() -> str:
    return os.environ["GREEN_API_ID_INSTANCE"]


def _api_token() -> str:
    return os.environ["GREEN_API_TOKEN_INSTANCE"]


def _method_url(method: str) -> str:
    return f"{GREEN_API_BASE_URL}/waInstance{_id_instance()}/{method}/{_api_token()}"


def _to_chat_id(phone_number: str) -> str:
    """Green API wants 'chatId' like '923001234567@c.us', not a bare number."""
    if "@" in phone_number:
        return phone_number
    digits = "".join(ch for ch in phone_number if ch.isdigit())
    return f"{digits}@c.us"


async def send_text(to: str, body: str) -> bool:
    """
    Send a plain text WhatsApp message to a phone number via Green API.
    Returns True on success, False on failure.
    Always returns — never raises — so an outage doesn't crash the
    webhook handler and cause retries to pile up.
    """
    url     = _method_url("sendMessage")
    payload = {
        "chatId": _to_chat_id(to),
        "message": body,
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            return True
    except Exception as e:
        logger.error("send_text failed to %s: %s", to, e)
        return False


async def get_media_url(download_url: str | None) -> str | None:
    """
    Green API's incoming webhook already gives us the direct downloadUrl
    for media messages (fileMessageData.downloadUrl) — unlike Meta, there's
    no media_id-to-URL exchange call needed.

    This function just passes the URL through, kept only so main.py's
    existing `await get_media_url(media_id)` call sites keep working
    unchanged.
    """
    if download_url and download_url.startswith("http"):
        return download_url
    logger.error("get_media_url: no valid downloadUrl provided (%s)", download_url)
    return None


async def download_media_bytes(media_url: str) -> bytes | None:
    """
    Downloads the actual file bytes from Green API's storage URL.
    No Authorization header needed — Green API download URLs are
    pre-signed and short-lived.

    Returns raw bytes, or None on failure.
    """
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(media_url)
            resp.raise_for_status()
            return resp.content
    except Exception as e:
        logger.error("download_media_bytes failed: %s", e)
        return None
