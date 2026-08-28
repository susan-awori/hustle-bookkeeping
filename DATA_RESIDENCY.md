# Hustle — Data residency

## Production region

**Render region chosen: Frankfurt (`frankfurt`).**

### Why Frankfurt (not Oregon/Ohio/Singapore)

Render’s available compute + Postgres regions are typically Oregon, Ohio, Frankfurt, and Singapore. Hustle’s users are informal traders **in Kenya**.

Approximate great-circle distance from Nairobi:

| Render region | Approx. distance from Nairobi | Notes |
| --- | --- | --- |
| **Frankfurt** | ~5,900 km | Closest Render region to Kenya; EU-grade data-center practices; lowest RTT of the set for East Africa via typical submarine routes (Mombasa–Europe). |
| Singapore | ~7,400 km | Farther; extra hop for many KE ISPs that peer toward Europe. |
| Ohio / Oregon | ~12,000+ km | Highest latency; worse for voice round-trips (STT + LLM + TTS). |

Structured ledger data lives **only** in the Render Postgres instance in **Frankfurt**. The FastAPI service is deployed in the **same region** so query traffic does not cross the Atlantic.

The React dashboard is a static site (Render static or CDN). It holds **no** ledger database. It only calls the Frankfurt API over HTTPS.

## What is *not* resident in Kenya

Kenya has no Render region. Frankfurt is the closest supported option. Voice bytes and transcripts also leave Kenya in transit to:

- ElevenLabs (vendor region per their account — configure EU if available)
- Anthropic API (vendor region per their account)

See `DATA_MAP.md` for what each vendor receives and how long we retain it.

## Local development

`docker-compose.yml` runs Postgres on the developer machine. That is **not** production residency. Production `DATABASE_URL` must point at the Frankfurt Render database only.

## Encryption

- In transit: TLS (Render HTTPS, vendor HTTPS).
- At rest: Render Postgres disk encryption as provided by the platform.
- Application-level: phone HMAC, PIN bcrypt; JWT signed with `JWT_SECRET`.
