"""
KhataAI — Week 4 | Phase 3 + Phase 4
Owner: Younas (routing, query answering, voice, digest trigger)
      Aaima  (whitelist, ledger write, debtor list, digest message, fallback)

Week 4 adds on top of Week 3:
  Phase 3: Intent classifier, earnings query, voice note, debtor query (Aaima)
  Phase 4: Monthly digest auto-send, manual DIGEST trigger
"""

import os
from datetime import datetime
from fastapi import FastAPI, Request, Response
from dotenv import load_dotenv

# Week 3 — carried forward
from app.whatsapp import send_text, get_media_url, download_media_bytes
from app.gemini_client import extract_receipt
from app.supabase_client import get_supabase, upload_receipt_image
from app.whitelist import is_whitelisted, REJECTION_MESSAGE
from app.rate_limit import is_within_daily_limit, increment_daily_count, LIMIT_REACHED_MESSAGE
from app.ledger import save_ledger_entry, confirmation_message, FAILED_OCR_MESSAGE, determine_is_paid

# Week 4 — new
from app.intent import classify, Intent
from app.ledger_query import handle_earnings_query
from app.voice import transcribe_and_classify, VOICE_FAILED_MESSAGE
from app.debtor import handle_debtor_query               # Aaima
from app.fallback import UNKNOWN_FALLBACK_MESSAGE        # Aaima
from app.digest_trigger import (
    fire_digest_for_user,
    run_digest_for_all_active_users,
    verify_cron_secret,
)

load_dotenv()

app = FastAPI(title="KhataAI — Week 4")


# ── Health ──────────────────────────────────────────────────────────────────
@app.get("/")
def health():
    return {"status": "ok", "service": "KhataAI", "week": 4}


# ── Phase 4: cron endpoint — Younas ─────────────────────────────────────────
@app.post("/internal/run-digest")
async def run_digest_endpoint(request: Request):
    """
    Called by Supabase pg_cron on the 1st of every month at 4am UTC.
    Protected by X-Cron-Secret header.
    """
    secret = request.headers.get("x-cron-secret")
    if not verify_cron_secret(secret):
        return Response(status_code=403)

    sent = await run_digest_for_all_active_users()
    return {"digests_sent": sent}


# ── Main webhook handler ─────────────────────────────────────────────────────
@app.post("/webhook")
async def receive_message(request: Request):
    payload = await request.json()
    message, phone_number = _extract_message(payload)
    if message is None:
        return Response(status_code=200)

    # FIRST: beta whitelist check — Aaima's code
    if not is_whitelisted(phone_number):
        await send_text(phone_number, REJECTION_MESSAGE)
        return Response(status_code=200)

    # Get or create user
    user = _get_or_create_user(phone_number)
    user_id = user["id"]

    # Classify intent — Younas
    message_type = message.get("type")
    text_body    = message.get("text", {}).get("body") if message_type == "text" else None
    intent       = classify(message_type, text_body)

    # Rate limit — only for AI-heavy operations (image + audio)
    if intent in (Intent.IMAGE, Intent.VOICE) and not is_within_daily_limit(phone_number):
        await send_text(phone_number, LIMIT_REACHED_MESSAGE)
        return Response(status_code=200)

    # ── Route by intent ──────────────────────────────────────────────────────

    if intent == Intent.IMAGE:
        await _handle_image(message, phone_number, user_id)

    elif intent == Intent.VOICE:
        # Phase 3 — Younas: voice note pipeline
        await _handle_voice(message, phone_number, user_id)

    elif intent == Intent.EARNINGS_QUERY:
        # Phase 3 — Younas: ledger query answering
        reply = handle_earnings_query(user_id, text_body)
        await send_text(phone_number, reply)

    elif intent == Intent.DEBTOR_QUERY:
        # Phase 3 — Aaima: debtor list
        reply = handle_debtor_query(user_id)
        await send_text(phone_number, reply)

    elif intent == Intent.MANUAL_DIGEST:
        # Phase 4 — Younas: manual test trigger
        await fire_digest_for_user(user_id, phone_number)

    else:
        # Aaima's fallback message
        await send_text(phone_number, UNKNOWN_FALLBACK_MESSAGE)

    return Response(status_code=200)


# ── Phase 2: image handler — Younas ─────────────────────────────────────────
async def _handle_image(message: dict, phone_number: str, user_id: str) -> None:
    media_id   = message["image"]["id"]
    caption    = message["image"].get("caption")

    await send_text(phone_number, "Receipt mil gayi! Abhi read kar raha hoon...")

    media_url = await get_media_url(media_id)
    if not media_url:
        await send_text(phone_number, FAILED_OCR_MESSAGE)
        return

    image_bytes = await download_media_bytes(media_url)
    if not image_bytes:
        await send_text(phone_number, FAILED_OCR_MESSAGE)
        return

    filename   = f"{media_id}.jpg"
    stored_url = upload_receipt_image(user_id, filename, image_bytes, "image/jpeg")
    image_url  = stored_url or media_url

    extracted = extract_receipt(image_bytes)
    if not extracted:
        await send_text(phone_number, FAILED_OCR_MESSAGE)
        return

    entry = save_ledger_entry(
        user_id=user_id,
        extracted=extracted,
        image_url=image_url,
        raw_text=str(extracted),
        caption=caption,
    )
    increment_daily_count(phone_number)
    await send_text(phone_number, confirmation_message(entry))


# ── Phase 3: voice handler — Younas ─────────────────────────────────────────
async def _handle_voice(message: dict, phone_number: str, user_id: str) -> None:
    """
    Downloads the voice note from Meta CDN, sends to Gemini for
    transcription + intent classification, then routes to the same
    handlers used for text and image messages.
    No new handlers needed — voice just adds an audio input path.
    """
    media_id = message["audio"]["id"]
    await send_text(phone_number, "Voice note sun raha hoon...")

    media_url = await get_media_url(media_id)
    if not media_url:
        await send_text(phone_number, VOICE_FAILED_MESSAGE)
        return

    audio_bytes = await download_media_bytes(media_url)
    if not audio_bytes:
        await send_text(phone_number, VOICE_FAILED_MESSAGE)
        return

    result = transcribe_and_classify(audio_bytes, mime_type="audio/ogg")
    if not result:
        await send_text(phone_number, VOICE_FAILED_MESSAGE)
        return

    voice_intent = result.get("intent", "UNKNOWN")

    if voice_intent == "RECEIPT":
        receipt = result.get("receipt")
        if not receipt or not receipt.get("amount"):
            await send_text(phone_number, VOICE_FAILED_MESSAGE)
            return

        extracted = {
            "date":   receipt.get("date"),
            "amount": receipt["amount"],
            "vendor": receipt.get("vendor") or "Unknown",
            "type":   receipt.get("type", "income"),
        }
        is_paid   = not receipt.get("is_udhaar", False)
        filename  = f"{media_id}.ogg"
        stored    = upload_receipt_image(user_id, filename, audio_bytes, "audio/ogg")
        audio_url = stored or media_url

        entry = save_ledger_entry(
            user_id=user_id,
            extracted=extracted,
            image_url=audio_url,
            raw_text=result.get("transcription", ""),
            caption="udhaar" if not is_paid else None,
        )
        increment_daily_count(phone_number)
        await send_text(phone_number, confirmation_message(entry))

    elif voice_intent == "EARNINGS_QUERY":
        transcription = result.get("transcription", "is mahine kitna kamaya?")
        reply = handle_earnings_query(user_id, transcription)
        await send_text(phone_number, reply)

    elif voice_intent == "DEBTOR_QUERY":
        reply = handle_debtor_query(user_id)
        await send_text(phone_number, reply)

    else:
        await send_text(phone_number, UNKNOWN_FALLBACK_MESSAGE)


# ── Utilities ────────────────────────────────────────────────────────────────
def _get_or_create_user(phone_number: str) -> dict:
    supabase = get_supabase()
    result   = supabase.table("users").select("*").eq("phone_number", phone_number).execute()
    if result.data:
        return result.data[0]
    insert = supabase.table("users").insert({"phone_number": phone_number, "is_active": True}).execute()
    return insert.data[0]


def _extract_message(payload: dict):
    """
    Green API sends a completely different webhook shape than Meta's Cloud
    API. Normalizes it into the same {"type": ..., "text"/"image"/"audio": ...}
    shape the rest of this file already expects, so nothing downstream
    (_handle_image, _handle_voice, intent classify) has to change.

    Note: for image/audio, "id" below is actually the Green API downloadUrl,
    not a media_id — whatsapp.get_media_url() just passes it straight through.
    """
    try:
        if payload.get("typeWebhook") != "incomingMessageReceived":
            return None, None

        phone_number = payload["senderData"]["sender"].split("@")[0]
        message_data = payload["messageData"]
        type_message = message_data.get("typeMessage")

        if type_message == "textMessage":
            body = message_data["textMessageData"]["textMessage"]
            return {"type": "text", "text": {"body": body}}, phone_number

        if type_message == "extendedTextMessage":
            body = message_data["extendedTextMessageData"]["text"]
            return {"type": "text", "text": {"body": body}}, phone_number

        if type_message == "imageMessage":
            file_data = message_data["fileMessageData"]
            return {
                "type": "image",
                "image": {"id": file_data["downloadUrl"], "caption": file_data.get("caption")},
            }, phone_number

        if type_message == "audioMessage":
            file_data = message_data["fileMessageData"]
            return {
                "type": "audio",
                "audio": {"id": file_data["downloadUrl"]},
            }, phone_number

        return None, None
    except (KeyError, IndexError, TypeError, AttributeError):
        return None, None
