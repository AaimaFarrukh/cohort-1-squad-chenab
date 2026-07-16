"""
KhataAI — Week 3 | WhatsApp Cloud API helper
Owner: Younas

Handles all outgoing calls to Meta's WhatsApp Business Cloud API:
  - Sending text messages back to the seller
  - Getting the real download URL for a media file (receipts arrive as media_id only)
  - Downloading the actual image bytes from Meta's CDN
"""

import os
import logging
import httpx

logger = logging.getLogger("khataai.whatsapp")

# Meta's base URL for the WhatsApp Cloud API
WHATSAPP_API_URL = "https://graph.facebook.com/v19.0"


def _headers() -> dict:
    """Auth headers for every Meta API call."""
    return {
        "Authorization": f"Bearer {os.environ['WHATSAPP_TOKEN']}",
        "Content-Type": "application/json",
    }


def _phone_number_id() -> str:
    return os.environ["WHATSAPP_PHONE_NUMBER_ID"]


async def send_text(to: str, body: str) -> bool:
    """
    Send a plain text WhatsApp message to a phone number.
    Returns True on success, False on failure.
    Always returns — never raises — so a Meta outage doesn't
    crash the webhook handler and cause Meta to retry forever.
    """
    url     = f"{WHATSAPP_API_URL}/{_phone_number_id()}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": body},
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(url, json=payload, headers=_headers())
            resp.raise_for_status()
            return True
    except Exception as e:
        logger.error("send_text failed to %s: %s", to, e)
        return False


async def get_media_url(media_id: str) -> str | None:
    """
    Phase 2 — Younas.

    WhatsApp webhook payloads give us a media_id for image messages,
    NOT the actual download URL. We must call Meta's media endpoint
    first to get the real URL, then download separately.

    Returns the download URL string, or None on failure.
    """
    url = f"{WHATSAPP_API_URL}/{media_id}"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, headers=_headers())
            resp.raise_for_status()
            return resp.json().get("url")
    except Exception as e:
        logger.error("get_media_url failed for media_id %s: %s", media_id, e)
        return None


async def download_media_bytes(media_url: str) -> bytes | None:
    """
    Phase 2 — Younas.

    Downloads the actual image bytes from Meta's CDN.
    The Authorization header is required here too — Meta CDN URLs
    are not publicly accessible even though they look like normal URLs.

    Returns raw bytes, or None on failure.
    """
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                media_url,
                headers={"Authorization": f"Bearer {os.environ['WHATSAPP_TOKEN']}"},
            )
            resp.raise_for_status()
            return resp.content
    except Exception as e:
        logger.error("download_media_bytes failed: %s", e)
        return None
