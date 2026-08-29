# Hustle & Buku

Voice-first bookkeeping for informal traders in Kenya. Speak mixed Kiswahili, Sheng, or English; Hustle transcribes (ElevenLabs), extracts ledger rows (Claude), confirms by voice, and stores books securely in Postgres.

Data handling is documented in [`DATA_MAP.md`](DATA_MAP.md) and [`DATA_RESIDENCY.md`](DATA_RESIDENCY.md) (Render **Frankfurt**, closest region to Kenya).

---

## 📂 Clean Repository Structure

```
hustle-bookkeeping/
├── backend/            # FastAPI Python Backend (Uvicorn, Alembic, SQLAlchemy)
├── buku/               # Buku Flutter Mobile App (Android & iOS)
├── .github/            # GitHub Actions CI/CD Pipeline
├── render.yaml         # Render Deployment Blueprint
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
   - `CORS_ORIGINS` = `*`
3. Set `ApiService.baseUrl` in `buku/lib/src/services/api_service.dart` to your Render API URL (e.g. `https://hustle-api.onrender.com`).

---

## 🔒 Security Snapshot

- Phone numbers stored as HMAC-SHA256; PINs as bcrypt; JWT access 15 minutes + refresh 7 days.
- Every ledger query filters by `trader_id` from the access token (strict multi-tenant isolation).
- Rate limits on auth and voice routes (`slowapi`).
- Structured logs allowlist only — see `backend/app/logging_policy.py`.
