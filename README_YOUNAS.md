# KhataAI — Week 3 | Younas's Code

## What this folder contains

| File | What it does |
|---|---|
| `app/main.py` | FastAPI app, WhatsApp webhook GET + POST, image handler, routing |
| `app/whatsapp.py` | Meta WhatsApp Cloud API calls (send text, get media URL, download bytes) |
| `app/gemini_client.py` | Gemini 1.5 Flash OCR — receipt image → structured JSON |
| `app/rate_limit.py` | Daily usage cap per user — prevents Gemini quota drain |
| `app/supabase_client.py` | Supabase singleton + receipt image upload to Storage |
| `requirements.txt` | Python dependencies |
| `.env.example` | All environment variables needed |

## What Aaima provides (you import these)

```python
from app.whitelist import is_whitelisted, REJECTION_MESSAGE
from app.ledger import save_ledger_entry, confirmation_message, FAILED_OCR_MESSAGE
```

Make sure Aaima's `whitelist.py` and `ledger.py` are in the same `app/` folder before running.

---

## Step 1 — Local setup

```bash
cd younas/
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Fill in .env with your actual keys
uvicorn app.main:app --reload --port 8000
```

---

## Step 2 — Deploy to Railway (do this before Meta webhook setup)

Meta needs a live HTTPS URL to verify the webhook. Deploy first, then configure Meta.

```bash
# Install Railway CLI
npm install -g @railway/cli

railway login
railway init          # Select "Empty project"
railway up            # Deploys the current folder

# Set all env vars in Railway dashboard → Variables
# (Copy from your .env file)
```

Your Railway URL will be: `https://YOUR-APP.up.railway.app`

Add a `Procfile` in the root:
```
web: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

---

## Step 3 — Meta WhatsApp Business API setup

1. Go to **developers.facebook.com** → Create App → Business type
2. Add **WhatsApp** product to your app
3. Go to **WhatsApp → API Setup**
4. Copy your **Phone Number ID** and generate a **Permanent Access Token**
5. Under **Webhook** → Edit:
   - Callback URL: `https://YOUR-RAILWAY-APP.up.railway.app/webhook`
   - Verify token: same string as `WHATSAPP_VERIFY_TOKEN` in your .env
6. Click **Verify and Save** — Meta sends a GET to your webhook to confirm
7. Subscribe to the **messages** field

---

## Step 4 — Test checklist (Phase 1)

Run these in order. Don't move to Phase 2 testing until Phase 1 passes fully.

- [ ] `GET /` returns `{"status": "ok"}`
- [ ] Meta webhook verification succeeds (Railway logs show the GET request)
- [ ] Unknown number WhatsApps the bot → receives rejection message
- [ ] Your whitelisted number (added by Aaima in schema.sql) → receives "Received! Processing..."

## Step 5 — Test checklist (Phase 2)

- [ ] Send a clear printed receipt photo → correct amount and vendor confirmed in Urdu
- [ ] Send a handwritten receipt photo → correct extraction
- [ ] Send a WhatsApp invoice screenshot → correct extraction
- [ ] Send an EasyPaisa confirmation screenshot → correct extraction
- [ ] Send a photo in bad lighting → graceful failure message (not a crash)
- [ ] Send 21 receipt photos → 21st gets the daily limit message

---

## Week 3 done when:

✅ You photograph a handwritten receipt, send it to the WhatsApp number, and get the correct amount and vendor confirmed back in Urdu within 10 seconds.
