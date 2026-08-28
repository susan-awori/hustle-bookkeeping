# Hustle — Security notes (MVP)

## Authentication

- Identifier: Kenyan phone number, normalized to E.164 (`+254…`), stored as HMAC-SHA256 (`PHONE_HASH_PEPPER`). HMAC is used instead of bcrypt so we can **look up** a trader on login without storing plaintext.
- Secret: 4–6 digit PIN, **bcrypt** (passlib), never logged.
- Session: stateless JWT. Access token **15 minutes**. Refresh token **7 days**, `type` claim must match. No server-side session table. Client may store **only** the token strings.

## Authorization / tenancy

Every ledger and audio query function is trader-scoped. Authenticated `trader_id` comes from the access token, never from a client-supplied id in the body for reads. See comments at the top of each repository module.

## Abuse controls

- `slowapi` rate limits: stricter on `/auth/*` and `/voice/*`.
- Max audio upload size and content-type allowlist.
- Pydantic strict schemas on every endpoint.

## Secrets

`app/config.py` is the **only** module that reads `ELEVENLABS_API_KEY`, `ANTHROPIC_API_KEY`, `DATABASE_URL`, `JWT_SECRET`, `PHONE_HASH_PEPPER`. Missing required secrets **abort startup**.

## Kenya DPA 2019 (alignment, not legal advice)

- Lawful basis: contract (bookkeeping service) + consent for optional voice-note storage.
- Minimization: no raw audio by default; hashed phone; no INFO logs of transcripts/amounts.
- Security: hashing, TLS, tenancy filters, rate limits.
- Retention: voice notes 30 days then hard delete; books retained as the product purpose.

The user query was truncated at the secrets-startup requirement; this MVP also includes input validation, rate limiting, HMAC phones, JWT pair, structured log allowlisting, and trader_id query discipline as specified above.
