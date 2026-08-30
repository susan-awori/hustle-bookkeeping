# Buku

> **Voice-First AI Bookkeeping Mobile App for Informal Traders in Kenya** 🇰🇪

Buku empowers local merchants (mama mboga, boda riders, kiosk owners) to record their daily sales, expenses, and customer debts simply by **speaking into their phone**. It transcribes spoken mixed Kiswahili, Sheng, or English using **ElevenLabs Scribe (`scribe_v1`)**, extracts structured financial transactions using **Claude Sonnet**, speaks a voice confirmation back to the merchant, and persists ledger records in a zero-config database.

---

## 🏗️ Repository Architecture

```text
hustle-bookkeeping/
├── backend/            # FastAPI Python Backend (SQLAlchemy, Uvicorn, Alembic, SQLite/Postgres)
│   ├── app/
│   │   ├── routers/    # Voice, Ledger, Auth endpoints
│   │   ├── services/   # ElevenLabs (STT/TTS) & Claude (LLM Ledger Parser)
│   │   └── models.py   # SQLAlchemy Ledger & Trader models (SQLite & Postgres compatible)
│   └── tests/          # Pytest unit & integration test suite (100% passing)
├── buku/               # Buku Flutter Mobile App (Android & iOS)
│   └── lib/
│       ├── main.dart   # App entrypoint (Zero-barrier instant access)
│       ├── src/
│       │   ├── models/ # Dart data models (LedgerEntry, Trader, VoiceParseResponse)
│       │   ├── screens/# Voice Deck, Sales Ledger, Debt Collectors, Reports
│       │   ├── services/# REST API Client & English/Swahili Localization Service
│       │   └── theme/  # Clean, high-contrast theme with large readable typography
├── render.yaml         # Render Cloud Deployment Blueprint
└── README.md
```

---

## 🌟 Key Features

1. **🎙️ Voice-First Merchant Deck**:
   - Tap the central microphone button to record live audio from your phone.
   - Powered by **ElevenLabs Scribe (`scribe_v1`)** with native Swahili & English speech recognition.
   - **Audio Talk-Back**: Speaks a spoken confirmation audio out loud back to the trader via **ElevenLabs Multilingual TTS (`eleven_multilingual_v2`)**.

2. **🧠 AI Ledger Extraction (Claude)**:
   - Converts unstructured voice transcripts (e.g. *"Niliuza nyanya kilo 5 KES 400 M-Pesa"*) into structured financial transactions (`sales`, `expenses`, `credit_given`, `credit_repaid`).

3. **🌍 English & Kiswahili Localization**:
   - 1-Tap header toggle (`🇬🇧 ENG` / `🇰🇪 SWA`) to switch languages dynamically across all screens.
   - English enabled by default with clear, high-contrast, large-font typography.

4. **📲 1-Click WhatsApp Debt Collector**:
   - View customers who owe money and launch pre-filled, personalized WhatsApp reminder messages in 1 tap.

5. **⚡ Quick POS Keypad**:
   - Fast numeric keypad for manual sales entries in busy market environments.

6. **🔒 Zero-Barrier Access & Strict Multi-Tenant Security**:
   - Instant guest/trader session initialization — zero login friction.
   - Every backend query strictly filters by `trader_id` to guarantee multi-tenant data isolation.

---

## 🧪 Automated Testing & Verification

The backend unit and integration test suite has been verified and passes **100%**:

```bash
============================== 8 passed in 4.73s ==============================
```

### Verified Test Cases:
- `tests/test_auth.py` — Authentication & JWT access/refresh token issue.
- `tests/test_ledger_actions.py` — Manual entries, financial stats computation, debt settling, deletion, and cross-trader security isolation.
- `tests/test_ledger_scoping.py` — Multi-tenant data scoping.
- `tests/test_logging_policy.py` — PII redaction and structured logging allowlist.
- `tests/test_phone.py` — Kenyan E.164 phone number normalization.

---

## 🛠️ Local Development Setup

### 1. Backend (FastAPI Python 3.12)

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Run migrations & start server
alembic upgrade head
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### 2. Mobile App (Buku Flutter)

```bash
cd buku
flutter pub get
flutter run
```

---

## 🚀 Live Cloud Deployment (Render)

Region: **Frankfurt** (`render.yaml`)

### Required Environment Variables on Render:
Set these in your Render Dashboard under `hustle-api` → **Environment** tab:

| Variable | Description |
|---|---|
| `ELEVENLABS_API_KEY` | Your ElevenLabs API key for Speech-to-Text (`scribe_v1`) & Text-to-Speech |
| `ANTHROPIC_API_KEY` | Your Anthropic Claude API key for structured ledger parsing |

### Live API Base URL:
`https://hustle-bookkeeping.onrender.com`
