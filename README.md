# Hustle

Voice-first bookkeeping for informal traders in Kenya. Speak mixed Kiswahili/English; Hustle transcribes (ElevenLabs), extracts ledger rows (Claude), confirms by voice, and stores books in Postgres.

Data handling is documented first in [`DATA_MAP.md`](DATA_MAP.md) and [`DATA_RESIDENCY.md`](DATA_RESIDENCY.md) (Render **Frankfurt**, closest region to Kenya).

## Local setup

1. Copy `.env.example` to `backend/.env` and replace every `replace-` value with real secrets (32+ random characters for `JWT_SECRET` and `PHONE_HASH_PEPPER`).
2. Start Postgres:

```bash
docker compose up -d
```

3. Backend:

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

4. Frontend:

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. The Vite proxy forwards `/api` to the API.

## Tests

```bash
cd backend
pytest
```

## Render production

Region: **Frankfurt** for API, cron, and Postgres (see `DATA_RESIDENCY.md`).

1. Create a Blueprint from `render.yaml`, or create the same services by hand.
2. In Render’s **Environment** panel (not in git), set:
   - `ELEVENLABS_API_KEY`
   - `ANTHROPIC_API_KEY`
   - `JWT_SECRET` (long random; **same value** on API and the audio-cleanup cron)
   - `PHONE_HASH_PEPPER` (long random; **same value** on API and cron)
   - `CORS_ORIGINS` = the static site origin, e.g. `https://hustle-web.onrender.com`
   - `VITE_API_URL` on the static site = `https://hustle-api.onrender.com` (no trailing slash)
3. `DATABASE_URL` is injected from the Frankfurt database. Do not paste it into source control.

Raw audio is **not** stored unless the trader opts in. Expired opt-in files are hard-deleted by `python -m app.jobs.cleanup_audio` (cron at 02:00 UTC plus an in-process job every 6 hours).

## Security snapshot

- Phone numbers stored as HMAC-SHA256; PINs as bcrypt; JWT access 15 minutes + refresh 7 days.
- Every ledger query filters by `trader_id` from the access token.
- Rate limits on auth and voice routes (`slowapi`).
- Structured logs allowlist only — see `backend/app/logging_policy.py`.
