"""
KhataAI — Week 3 | Phase 1 + Phase 2
Owner: Younas

Younas owns:
  - FastAPI app setup
  - WhatsApp webhook GET verification
  - WhatsApp webhook POST receiver
  - Image download from Meta CDN
  - Gemini OCR call
  - API rate limiting check + increment

Aaima owns (imported from aaima/):
  - Supabase schema (schema.sql)
  - Basic reply message
  - Beta user whitelist check
  - Write to ledger + Urdu confirmation
  - Error messages
"""

import os
from fastapi import FastAPI, Request, Response
from dotenv import load_dotenv

from app.whatsapp import send_text, get_media_url, download_media_bytes
from app.gemini_client import extract_receipt
from app.supabase_client import get_supabase, upload_receipt_image
from app.whitelist import is_whitelisted, REJECTION_MESSAGE          # Aaima
from app.rate_limit import is_within_daily_limit, increment_daily_count, LIMIT_REACHED_MESSAGE  # Younas
from app.ledger import save_ledger_entry, confirmation_message, FAILED_OCR_MESSAGE  # Aaima

load_dotenv()

app = FastAPI(title="KhataAI — Week 3")


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
@app.get("/")
def health():
    return {"status": "ok", "service": "KhataAI", "week": 3}


# ---------------------------------------------------------------------------
# Phase 1 — Younas
# WhatsApp webhook verification.
# Meta sends a GET request with a challenge token when you first set up
# the webhook. This endpoint must echo the challenge back or Meta rejects it.
# ---------------------------------------------------------------------------
@app.get("/webhook")
def verify_webhook(request: Request):
    mode      = request.query_params.get("hub.mode")
    token     = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    expected_token = os.environ["WHATSAPP_VERIFY_TOKEN"]
    if mode == "subscribe" and token == expected_token:
        # Return the challenge as plain text — Meta checks for exactly this.
        return Response(content=challenge, media_type="text/plain")
    return Response(status_code=403)


# ---------------------------------------------------------------------------
# Phase 1 + 2 — Younas (routing) + Aaima (whitelist, reply, ledger write)
# Main incoming message handler.
# ---------------------------------------------------------------------------
@app.post("/webhook")
async def receive_message(request: Request):
    payload = await request.json()

    # Pull the message and sender number out of Meta's nested payload.
    message, phone_number = _extract_message(payload)
    if message is None:
        # Meta also sends delivery receipts and read receipts to this endpoint.
        # They have no "messages" key — just return 200 and ignore them.
        return Response(status_code=200)

    # -------------------------------------------------------------------
    # FIRST CHECK — Aaima's whitelist (Phase 1)
    # Must run before anything else — no DB writes, no AI calls, nothing.
    # -------------------------------------------------------------------
    if not is_whitelisted(phone_number):
        await send_text(phone_number, REJECTION_MESSAGE)
        return Response(status_code=200)

    # -------------------------------------------------------------------
    # SECOND CHECK — Younas's rate limiter (Phase 1)
    # Only applies to image messages (the ones that consume Gemini credits).
    # Text messages are cheap and not rate-limited in Week 3.
    # -------------------------------------------------------------------
    message_type = message.get("type")

    if message_type == "image" and not is_within_daily_limit(phone_number):
        await send_text(phone_number, LIMIT_REACHED_MESSAGE)
        return Response(status_code=200)

    # -------------------------------------------------------------------
    # Phase 1 — Aaima's basic reply
    # For any non-image message in Week 3, just acknowledge.
    # -------------------------------------------------------------------
    if message_type != "image":
        await send_text(phone_number, "Received! Processing...")
        return Response(status_code=200)

    # -------------------------------------------------------------------
    # Phase 2 — Younas: image download + OCR | Aaima: ledger write + reply
    # -------------------------------------------------------------------
    await _handle_image_message(message, phone_number)
    return Response(status_code=200)


# ---------------------------------------------------------------------------
# Phase 2 — Younas
# Download the receipt image from Meta's CDN and run Gemini OCR on it.
# Then hands off to Aaima's ledger writer.
# ---------------------------------------------------------------------------
async def _handle_image_message(message: dict, phone_number: str) -> None:
    media_id = message["image"]["id"]
    caption  = message["image"].get("caption")

    # Tell the user we received it while we process.
    await send_text(phone_number, "Receipt mil gayi! Abhi read kar raha hoon...")

    # Step 1 — Younas: get the real download URL from Meta
    # The webhook payload only gives us a media_id, not the image itself.
    media_url = await get_media_url(media_id)
    if media_url is None:
        await send_text(phone_number, FAILED_OCR_MESSAGE)
        return

    # Step 2 — Younas: download the actual image bytes
    image_bytes = await download_media_bytes(media_url)
    if image_bytes is None:
        await send_text(phone_number, FAILED_OCR_MESSAGE)
        return

    # Step 3 — Younas: upload to Supabase Storage for permanent storage.
    # Meta's CDN URLs expire — we need our own copy.
    # get_or_create_user is called here to get the user_id for the storage path.
    user = _get_or_create_user(phone_number)
    user_id = user["id"]

    filename  = f"{media_id}.jpg"
    stored_url = upload_receipt_image(user_id, filename, image_bytes, "image/jpeg")
    image_url  = stored_url or media_url   # fallback to CDN URL if upload fails

    # Step 4 — Younas: call Gemini to extract structured data from the receipt
    extracted = extract_receipt(image_bytes)
    if extracted is None:
        await send_text(phone_number, FAILED_OCR_MESSAGE)
        return

    # Step 5 — Aaima: write to ledger + send Urdu confirmation
    entry = save_ledger_entry(
        user_id=user_id,
        extracted=extracted,
        image_url=image_url,
        raw_text=str(extracted),
        caption=caption,
    )

    # Step 6 — Younas: increment the daily rate limit counter
    increment_daily_count(phone_number)

    await send_text(phone_number, confirmation_message(entry))


# ---------------------------------------------------------------------------
# Utility — Younas
# Gets or creates a user row in Supabase from a phone number.
# Week 3 keeps this simple — no opt-in flow yet, that's Phase 5 (Week 5).
# ---------------------------------------------------------------------------
def _get_or_create_user(phone_number: str) -> dict:
    supabase = get_supabase()
    result = (
        supabase.table("users")
        .select("*")
        .eq("phone_number", phone_number)
        .execute()
    )
    if result.data:
        return result.data[0]

    insert = (
        supabase.table("users")
        .insert({"phone_number": phone_number, "is_active": True})
        .execute()
    )
    return insert.data[0]


# ---------------------------------------------------------------------------
# Utility — Younas
# Pulls the first inbound message + sender number out of Meta's deeply
# nested webhook payload. Returns (None, None) for non-message payloads
# (delivery receipts, read receipts, etc.).
# ---------------------------------------------------------------------------
def _extract_message(payload: dict):
    try:
        value    = payload["entry"][0]["changes"][0]["value"]
        messages = value.get("messages")
        if not messages:
            return None, None
        message      = messages[0]
        phone_number = message["from"]
        return message, phone_number
    except (KeyError, IndexError):
        return None, None
