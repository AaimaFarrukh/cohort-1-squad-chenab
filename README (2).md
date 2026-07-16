# KhataAI — Week 3
**Comebck Pakistan Cohort 1 | Phase 1 + Phase 2**

AI bookkeeper for Pakistani social media sellers.
Sellers forward WhatsApp receipt photos → Gemini reads them → ledger saved → Urdu confirmation sent back.

---

## Who built what

| File | Owner | What it does |
|---|---|---|
| `app/main.py` | Younas | FastAPI app, webhook routing, image handler |
| `app/whatsapp.py` | Younas | Meta WhatsApp Cloud API calls |
| `app/gemini_client.py` | Younas | Gemini 1.5 Flash OCR — receipt → JSON |
| `app/supabase_client.py` | Younas | Supabase singleton + image storage upload |
| `app/rate_limit.py` | Younas | Daily usage cap — prevents Gemini quota drain |
| `app/whitelist.py` | Aaima | Beta user check — first check on every message |
| `app/ledger.py` | Aaima | DB write + all Urdu reply messages |
| `schema.sql` | Aaima | Complete Supabase schema — run once |

---

## Week 3 scope — Phase 1 + Phase 2 only

**In scope:**
- WhatsApp webhook live on Railway
- Beta user whitelist
- Daily rate limiting
- Receipt OCR and ledger save
- Urdu confirmation messages

**Not in scope this week (coming in Week 4+):**
- Urdu chat queries ("is mahine kitna kamaya?")
- Voice note support
- Monthly digest
- Onboarding / opt-in flow

---

## Setup — do these in order

### 1. Aaima — Supabase setup
1. Create a Supabase project at supabase.com
2. Enable `pg_cron` extension: Database → Extensions → pg_cron → Enable
3. Go to SQL Editor → New query → paste `schema.sql` → Run
4. Go to Storage → Create bucket named `receipts` (Public: OFF)
5. Go to Table Editor → `beta_users` → add your team's WhatsApp numbers
   - Format: `+923001234567` (with country code)

### 2. Younas — Local run
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Fill in .env with keys from Supabase, Google AI Studio, and Meta
uvicorn app.main:app --reload --port 8000
```

### 3. Younas — Deploy to Railway
```bash
npm install -g @railway/cli
railway login
railway init
railway up
```
Set all env vars in Railway → Variables tab.

### 4. Younas — Meta WhatsApp API
1. developers.facebook.com → Create App → Business
2. Add WhatsApp product
3. Copy Phone Number ID + generate Permanent Access Token
4. Webhook URL: `https://YOUR-APP.up.railway.app/webhook`
5. Verify token: same as `WHATSAPP_VERIFY_TOKEN` in .env
6. Subscribe to `messages` field

### 5. Aaima — Add your number to beta_users
```sql
insert into beta_users (phone_number, name, added_by)
values ('+923001234567', 'Your Name', 'aaima');
```

---

## Environment variables

```env
WHATSAPP_TOKEN=
WHATSAPP_PHONE_NUMBER_ID=
WHATSAPP_VERIFY_TOKEN=
GEMINI_API_KEY=
GEMINI_MODEL=gemini-1.5-flash
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=
SUPABASE_STORAGE_BUCKET=receipts
DAILY_RECEIPT_LIMIT=20
```

---

## Full test checklist — Week 3 done when all pass

**Phase 1 — Foundation**
- [ ] `GET /` → `{"status": "ok"}`
- [ ] Meta webhook verification succeeds
- [ ] Unknown number → rejection message in Urdu
- [ ] Whitelisted number → "Received! Processing..."
- [ ] 21st receipt from same number → daily limit message

**Phase 2 — OCR Pipeline**
- [ ] Clear printed receipt → correct amount + vendor confirmed in Urdu
- [ ] Handwritten receipt → correct extraction
- [ ] WhatsApp invoice screenshot → correct extraction
- [ ] EasyPaisa / JazzCash screenshot → correct extraction
- [ ] Bad lighting photo → graceful failure message (no crash)
- [ ] Receipt with caption "udhaar" → is_paid = false in Supabase
- [ ] Ledger row appears in Supabase Table Editor after every scan

**Week 3 complete when:**
You photograph a handwritten receipt, send it to the WhatsApp number,
and get the correct amount and vendor confirmed back in Urdu within 10 seconds.
