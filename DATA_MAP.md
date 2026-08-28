# Hustle — Data Map

This document lists **every place user data is created, stored, transmitted, or deleted** in the Hustle MVP. It is the source of truth for security review and Kenya Data Protection Act (2019) purpose limitation.

Hustle is a voice-first bookkeeping agent. Users speak mixed Swahili/English; we transcribe, extract ledger entries, confirm by voice, and persist structured books.

---

## 1. Identity and authentication

| Data | Created | Stored | Transmitted | Deleted / retained |
| --- | --- | --- | --- | --- |
| Phone number (Kenya E.164) | Registration (`POST /api/v1/auth/register`) | **Never stored in plaintext.** HMAC-SHA256 of the normalized number with `PHONE_HASH_PEPPER` in `traders.phone_number` (column holds the hash; unique). | Sent once from browser → Render API over HTTPS. Not sent to ElevenLabs or Anthropic. | Retained while the trader account exists. Account deletion (future) must drop the hash. |
| PIN (4–6 digits) | Registration and login | **Never stored in plaintext.** bcrypt hash in `traders.pin_hash`. | HTTPS to Render API only. | Same as account lifetime. bcrypt hash is not reversible. |
| Display name | Registration | `traders.display_name` in Render Postgres (Frankfurt). | HTTPS to Render API. Not sent to ElevenLabs. May be included in Claude confirmation phrasing only as already-known session context — **not** in the default parse prompt. | Account lifetime. |
| JWT access token (15 min) | Login / refresh | **Not stored on the server.** Client holds the token string only (memory / `sessionStorage`). | Authorization header to Render API. | Expires in 15 minutes. |
| JWT refresh token (7 days) | Login / refresh | **Not stored on the server** (stateless JWT with `type=refresh`). Client holds the token string only. | HTTPS body to `/api/v1/auth/refresh`. | Expires in 7 days. Rotation: new pair issued on refresh. |

**Not logged** at INFO or above: phone numbers, PINs, tokens.

---

## 2. Voice, transcripts, and confirmation audio

| Data | Created | Stored | Transmitted | Deleted / retained |
| --- | --- | --- | --- | --- |
| Raw microphone audio | Browser `MediaRecorder` | **Default: nowhere.** In-memory `bytes` on the API process only. | Browser → Render API (multipart). Render API → **ElevenLabs Speech-to-Text**. | Buffer discarded immediately after ElevenLabs returns a transcript (`del` + no file write). Browser blob revoked after upload. |
| Opt-in voice notes | Same upload with `save_voice_notes=true` (trader preference or per-request). | `audio_logs.s3_or_storage_path` points at local `AUDIO_STORAGE_PATH` (or optional object storage). `expires_at` = created_at + **30 days**. | Same as above, plus write to storage after STT. | Scheduled job `cleanup-expired-audio` **hard-deletes** expired files and rows. |
| Transcript (STT text) | ElevenLabs STT response | `ledger_entries.raw_transcript` (audit). `audio_logs.transcript` only when an `audio_logs` row is created (opt-in). | ElevenLabs → Render API. Render API → **Anthropic Claude** as the parse input. Confirmation TTS text is a **summary**, not a replay of the full transcript. | Ledger transcript retained for the life of the entry (correction/audit). Opt-in `audio_logs.transcript` deleted with the row at `expires_at`. |
| Confirmation TTS audio | ElevenLabs Text-to-Speech | **Not persisted.** Returned to the client as a short-lived audio blob (base64 in JSON). | Render API → ElevenLabs TTS → browser playback. | Discarded after response; client may play once. Not written to `audio_logs`. |

**ElevenLabs retention:** We do not enable ElevenLabs workspace history for this product path. Treat vendor-side processing as **transient inference**. Review ElevenLabs’ current DPA and retention settings before production traffic; disable any “keep audio for quality” workspace option.

**Anthropic retention:** Transcript text is sent to Claude (`claude-sonnet-4-6`) for structured extraction only. Use Anthropic API with no training on data (API default for paid workspaces — confirm org setting). We do not send phone numbers, PINs, or trader UUIDs in the parse prompt (we send transcript + extraction schema only).

---

## 3. Structured ledger (books)

| Data | Created | Stored | Transmitted | Deleted / retained |
| --- | --- | --- | --- | --- |
| Entry type, item description, amount (KES), counterparty, settled flag | After voice confirm (`POST /api/v1/ledger/confirm`) or equivalent confirm payload | **Only** Render Postgres `ledger_entries`. Never in logs at INFO+. Never in ElevenLabs. Amounts are **not** sent back to Claude after persist. | HTTPS between browser and Render API. | Retained for the life of the trader account (books of account). No soft-delete in MVP. |
| `trader_id` foreign keys | Insert time | Postgres; all ledger/audio queries **must** filter by authenticated `trader_id`. | Internal DB only. Logs may include a **hash** of trader_id (allowlist), never the raw UUID at INFO+. | Account lifetime. |

---

## 4. Third-party services (complete list)

| Service | Data it receives | Why | Retention (our policy) |
| --- | --- | --- | --- |
| **Render Postgres** (Frankfurt) | Hashed phone, PIN hash, display name, all ledger rows, optional audio_log metadata | System of record | Account lifetime except `audio_logs` (30 days). |
| **Render** (compute, Frankfurt API) | In-memory audio, request bodies during processing | Hosting | Process memory only; no raw audio on disk by default. |
| **ElevenLabs** | Audio bytes (STT); confirmation sentence (TTS) | Speech in/out | Transient processing; no product-side archive. |
| **Anthropic Claude** | Transcript text + JSON schema instructions | Extract structured entries | Transient API inference; no product-side archive. |

No other third parties (no analytics SDK, no Sentry in MVP, no CDN logging of bodies). If error tracking is added later, this file must be updated first.

---

## 5. Logging (application)

See `backend/app/logging_policy.py`.

**Allowlisted fields only:** `event`, `entry_type`, `timestamp`, `trader_id_hash`, `http_method`, `http_path` (no query string), `status_code`, `duration_ms`, `error_class` (not message if it might contain user text).

**Never at INFO or above:** full transcripts, phone numbers, PINs, tokens, ledger amounts, item descriptions, counterparty names, raw audio paths that include user ids in the clear.

---

## 6. Deletion summary

| Trigger | What is deleted |
| --- | --- |
| End of STT request (default) | In-memory audio buffer |
| `expires_at` on `audio_logs` | File at `s3_or_storage_path` + database row (hard delete) |
| End of TTS response | Server-side TTS bytes (not stored) |
| Token expiry | Access/refresh JWTs become invalid; nothing to delete server-side |

Account-wide erasure is not in this MVP API; when added it must delete `ledger_entries`, `audio_logs` (+ files), and `traders` in one transaction and be documented here.

---

## 7. Data flow (happy path)

1. Trader authenticates (phone + PIN) → JWT.
2. Browser records audio → HTTPS multipart to `/api/v1/voice/parse`.
3. API holds audio in RAM → ElevenLabs STT → **discard audio**.
4. Transcript → Claude → structured candidate entries (not yet committed).
5. Confirmation sentence → ElevenLabs TTS → browser plays audio.
6. Trader confirms → candidates written to Postgres `ledger_entries` with `raw_transcript`.
7. Dashboard reads ledger **only** with `WHERE trader_id = current_user`.
