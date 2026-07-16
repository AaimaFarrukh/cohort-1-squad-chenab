# KhataAI — Week 4
**Comebck Pakistan Cohort 1 | Phase 3 + Phase 4 (built on top of Week 3)**

---

## Who built what

### Week 3 (carried forward)
| File | Owner |
|---|---|
| `app/main.py` | Younas |
| `app/whatsapp.py` | Younas |
| `app/gemini_client.py` | Younas |
| `app/supabase_client.py` | Younas |
| `app/rate_limit.py` | Younas |
| `app/whitelist.py` | Aaima |
| `app/ledger.py` | Aaima |
| `schema.sql` | Aaima |

### Week 4 (new this week)
| File | Owner | What it does |
|---|---|---|
| `app/intent.py` | Younas | Classifies every message into an intent |
| `app/ledger_query.py` | Younas | Answers earnings questions from real ledger data |
| `app/voice.py` | Younas | Voice note transcription + classification via Gemini |
| `app/digest_trigger.py` | Younas | Monthly digest scheduler + manual DIGEST trigger |
| `app/debtor.py` | Aaima | "Kaun hisaab mein hai?" — unpaid invoice list |
| `app/fallback.py` | Aaima | Unknown query message |
| `app/digest_message.py` | Aaima | Monthly Urdu digest content builder |
| `schema_week4_additions.sql` | Aaima | Week 4 schema additions — run after schema.sql |

---

## Setup — Week 4 additions

### 1. Run schema_week4_additions.sql
In Supabase SQL Editor, run `schema_week4_additions.sql` AFTER `schema.sql` from Week 3.

**Before running the cron job:**
- Deploy to Railway first to get your live URL
- Replace `YOUR-RAILWAY-URL` and `YOUR-CRON-SECRET` in the file
- Then run just the cron.schedule() part

### 2. Enable pg_net extension (needed for digest cron)
Supabase Dashboard → Database → Extensions → Search `pg_net` → Enable

### 3. Environment variables (no changes from Week 3)
Same `.env` as Week 3 — no new variables needed.

---

## Full test checklist — Week 4 done when all pass

### Phase 3 — Urdu Chat
- [ ] Type "is mahine kitna kamaya?" → correct earnings summary in Urdu
- [ ] Type "kaun hisaab mein hai?" → debtor list or "sab clear hai"
- [ ] Type "pichle mahine ka hisaab?" → correct previous month summary
- [ ] Type something random → helpful fallback message
- [ ] Send a voice note saying an amount → receipt logged correctly
- [ ] Send a voice note asking "kitna kamaya?" → earnings summary returned
- [ ] Send a voice note asking about debtors → debtor list returned

### Phase 4 — Monthly Digest
- [ ] Type "digest" → monthly digest arrives immediately
- [ ] Digest shows correct income, expense, net profit
- [ ] Digest shows correct debtor list (or "sab ne payment kar di")
- [ ] POST /internal/run-digest with correct header → digests sent
- [ ] POST /internal/run-digest with wrong header → 403 returned

### Week 4 complete when:
A real seller (not a team member) asks "is mahine kya hua?" and gets
a correct Urdu summary back without any help from the team.
