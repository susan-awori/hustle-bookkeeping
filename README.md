# Hustle & Buku

Voice-first bookkeeping for informal traders in Kenya. Speak mixed Kiswahili, Sheng, or English; Hustle transcribes (ElevenLabs), extracts ledger rows (Claude), confirms by voice, and stores books securely in Postgres.

Built for **Cursor Kenya Build Night** 🇰🇪

## Why this exists

Millions of small traders in Kenya — mama mboga, kiosk owners, boda riders, kinyozi operators — run their business entirely on memory or a notebook that gets lost, rained on, or abandoned after a long day. That's not a discipline problem, it's a friction problem: writing structured entries mid-sale, at a kiosk, with a queue, just doesn't happen.

No records also means no access to credit — banks and SACCOs want financial history to lend against, and a notebook isn't bankable data.

Hustle removes the friction: traders **speak** what happened — a sale, an expense, credit given to a customer — and get back a clean, structured ledger. No typing, no menus, no literacy requirement.

> *"Nimeuza sukuma mia moja, na Mary ameshikilia hamsini."*
> → Sale: 100 KES (sukuma wiki), Credit given to Mary: 50 KES

Data handling is documented in [`DATA_MAP.md`](DATA_MAP.md) and [`DATA_RESIDENCY.md`](DATA_RESIDENCY.md) (Render **Frankfurt**, closest region to Kenya).

## Theme & Tools

- **Theme:** AI agents and automation / Solutions for African communities
- **Built with:** [Cursor](https://cursor.sh) · [ElevenLabs](https://elevenlabs.io) (speech-to-text & text-to-speech) · [Render](https://render.com) (backend, cron, and Postgres hosting)

---

## How it works — the core loop

1. **Speak** — trader records a voice note describing a sale, expense, or credit given
2. **Transcribe** — audio → text via ElevenLabs STT
3. **Parse** — transcript → structured ledger row via Claude (`type`, `item`, `amount`, `counterparty`, `settled`)
4. **Confirm** — trader reviews/corrects the parsed entry, Hustle reads it back via ElevenLabs TTS
5. **Ledger updates** — Daftari feed shows today's sales, outstanding credit, and weekly totals, scoped strictly to that trader

---

## 📂 Clean Repository Structure

```
hustle-bookkeeping/
├── backend/            # FastAPI Python Backend (Uvicorn, Alembic, SQLAlchemy)
├── buku/               # Buku Flutter Mobile App (Android & iOS)
├── .github/            # GitHub Actions CI/CD Pipeline
├── render.yaml         # Render Deployment Blueprint
├── DATA_MAP.md         # Where every piece of data lives, and for how long
├── DATA_RESIDENCY.md   # Region choice and rationale
└── README.md
```

---

## 📱 Flutter Mobile App (`buku/`)

The mobile application is built with **Flutter** featuring:
- **Smart Mic & Sheng Prompt Simulator**: Low-latency voice recording with 1-click Sheng prompt testing.
- **Daftari Feed & POS Keypad**: Interactive ledger feed with tactile 0-9 keypad for quick manual entries in noisy markets.
- **📲 1-Click WhatsApp Debt Collector**: Instant WhatsApp link generator to send personalized Swahili reminders to debtors.
- **Safaricom Green & M-Pesa Gold Theme**: High-contrast, sunlight-readable UI tailored for Kenyan traders.

### Running Buku Mobile App:
```bash
cd buku
flutter pub get
flutter run
```

---

## 🛠️ Local Backend Setup

1. Copy `.env.example` to `backend/.env`.
2. Start Postgres:
```bash
docker compose up -d
```
3. Backend Setup:
```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

---

## 🧪 Tests

```bash
cd backend
.venv/bin/pytest
```

---

## 🚀 Render Backend Deployment

Region: **Frankfurt** for API, cron, and Postgres (see `DATA_RESIDENCY.md`).

1. Create a Blueprint on Render using `render.yaml`.
2. Set Environment Variables in Render:
   - `ELEVENLABS_API_KEY`
   - `ANTHROPIC_API_KEY`
   - `JWT_SECRET` (32+ random characters)
   - `PHONE_HASH_PEPPER` (32+ random characters)
   - `CORS_ORIGINS` = *(set to your deployed app's actual origin before demo/production — see note below)*
3. Set `ApiService.baseUrl` in `buku/lib/src/services/api_service.dart` to your Render API URL (e.g. `https://hustle-api.onrender.com`).

---

## 🔒 Security Snapshot

- Phone numbers stored as HMAC-SHA256; PINs as bcrypt; JWT access 15 minutes + refresh 7 days.
- Every ledger query filters by `trader_id` from the access token (strict multi-tenant isolation).
- Rate limits on auth and voice routes (`slowapi`).
- Structured logs allowlist only — see `backend/app/logging_policy.py`.
- Raw audio is processed in-memory and discarded after transcription by default — not persisted unless a trader explicitly opts in.

> **Note:** `CORS_ORIGINS = *` is fine for local testing but should be locked to your actual frontend/mobile origin before you consider this beyond a hackathon demo — a wildcard origin defeats the point of the auth work above.

---

## What's intentionally out of scope (MVP)

- No M-Pesa integration (amounts are manually spoken/entered)
- No offline/USSD fallback for feature phones (biggest roadmap item — many traders don't have smartphones)
- No real credit-scoring or loan matching — the ledger is designed to be *loan-ready data*, not a lending product itself

## Roadmap (post-hackathon)

- [ ] SMS/USSD fallback for feature phones
- [ ] Multi-language support beyond Kiswahili/Sheng/English (Kikuyu, Luo)
- [ ] M-Pesa statement reconciliation
- [ ] Exportable financial summary for loan applications
- [ ] Lock CORS to production origin, rotate JWT/HMAC secrets out of demo values

---

## Team

*Susan Awori, Alex Nyambura and Mary Wangoi*

Built at Cursor Kenya Build Night 🇰🇪

