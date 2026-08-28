# Hustle: UI polish, frontend hardening, and pitch narrative

Date: 2026-08-29
Status: Approved by user, ready for implementation planning

## Context

Hustle is a voice-first bookkeeping MVP for informal Kenyan traders (React + Vite frontend,
FastAPI backend, ElevenLabs for STT/TTS, Claude for ledger extraction, Postgres, deployed via
Render). The backend is solid: 6/6 tests pass, uses current APIs, has auth/rate-limiting/logging
already in place. The frontend builds cleanly with no errors.

This is for a hackathon demo, 1-2 days out. The ask was broad ("make the UI better", "modern
tech, no bugs", "validate the idea", "use ElevenLabs", "deploy to Render"). Investigation showed:
ElevenLabs/Claude are already integrated correctly, `render.yaml` is already correct and ready to
deploy, and the backend has no real bugs. So the actual scope, after decomposing with the user, is
three independent workstreams. **Render deployment is explicitly out of scope** — the user will
handle that themselves.

## Scope

1. Frontend component refactor + visual redesign (same warm/local palette, executed properly)
2. Frontend bug fixes / robustness (remove a fragile browser API dependency, fix a null-deref,
   improve error/loading states)
3. `PITCH.md` — a pitch narrative doc for judges (not code)

Explicitly out of scope: backend changes (already correct/tested), Render deployment walkthrough,
new product features (analytics, M-Pesa integration, etc.) — those are pitch "roadmap" items only.

## 1. Component structure

Split `frontend/src/App.jsx` (currently ~320 lines handling auth, recording, transcript, and
ledger in one component) into focused components under `frontend/src/components/`:

- `AuthScreen.jsx` — login/register card (mode tabs, phone/PIN/name fields, submit)
- `Header.jsx` — top bar: trader name + logout button
- `MicPanel.jsx` — record button, recording state animation, voice-notes opt-in checkbox
- `TranscriptCard.jsx` — transcript display, confirmation audio player, parsed entry preview,
  confirm/cancel actions, "needs clarification" message
- `LedgerTable.jsx` — the ledger/books table with empty state
- `Toast.jsx` — dismissible error/status banner

`App.jsx` remains the owner of state and data flow (auth tokens, API calls, MediaRecorder logic)
and composes these components via props. No routing library — this is a two-screen app
(auth vs. main), react-router would be unnecessary overhead.

Interfaces: each component takes plain data + callback props (e.g. `MicPanel` takes
`recording`, `busy`, `saveVoiceNotes`, `onToggleMic`, `onToggleVoiceNotes`). No component reaches
into `api.js` directly except `App.jsx` — keeps components testable/understandable in isolation.

## 2. Bug fixes / robustness

1. **Remove the browser `SpeechRecognition` "live draft" path** (`startLiveDraft`,
   `recognitionRef`, `liveDraft` state). It only runs in Chrome/Android (`window.SpeechRecognition
   || window.webkitSpeechRecognition`), silently no-ops elsewhere, and is fully redundant with the
   real ElevenLabs transcript returned by `/api/v1/voice/parse`. It exists only for a cosmetic
   "live captions while recording" effect. Replace with a CSS-only recording-in-progress
   animation (pulsing waveform bars) in `MicPanel` — removes a second, browser-inconsistent
   transcription path that could break live during a demo.
2. **Fix `toggleVoiceNotes` null-deref**: `const next = !me.save_voice_notes` throws if `me` is
   momentarily null. Guard with `me?.save_voice_notes`.
3. **Replace the single generic `error` string** with a `Toast` component that surfaces the actual
   failure message and auto-dismisses after a few seconds — currently one `error` state is shared
   between the auth screen and the main screen and can be overwritten silently.
4. **Distinguish mic-permission-denied / no-microphone-available from "audio didn't transcribe"**
   — currently both funnel into the same generic Kiswahili error message in `toggleMic`'s catch
   block. Check `error.name` from `getUserMedia` rejection and show a more specific message for
   `NotAllowedError` / `NotFoundError`.

No backend changes. No new backend dependencies.

## 3. Visual redesign

Keep the existing warm paper/green palette (`--paper`, `--green`, `--card`, `--green-hot` in
`styles.css`) as the base — it's a good, distinctive choice for the product — but execute it with
more care:

- Define a real type scale and spacing scale as CSS custom properties (replacing today's ad hoc
  rem values scattered through the stylesheet)
- Add `lucide-react` (tree-shakeable, ~2kb/icon) for a mic icon, checkmark, logout icon, phone/PIN
  field icons — replacing plain text-only buttons
- Redesign the mic button as the clear visual centerpiece: larger, a subtle idle pulse, and a
  distinct recording state using animated waveform bars (CSS keyframes) instead of just a color
  swap
- Add a skeleton/loading state for the ledger table while `loadMeAndBooks` is in flight, and a
  friendlier empty state
- Subtle CSS transitions on card appearance and state changes (no animation library — plain CSS
  transitions/keyframes are sufficient for this scope)

No Tailwind migration — lower risk given the 1-2 day window, and the current stylesheet is small
enough that hand-tuned CSS custom properties are sufficient.

## 4. Pitch narrative (`PITCH.md`)

A new markdown doc at the repo root (not code), covering:

- **Problem**: informal Kenyan traders (mama mboga, kiosk owners, boda riders) rarely keep formal
  books due to literacy/time/tooling barriers, making it hard to track profit, access credit, or
  prove income.
- **Solution**: speak a transaction in Kiswahili/Sheng/English; Hustle transcribes it (ElevenLabs
  STT), extracts structured ledger rows (Claude), reads back a spoken confirmation (ElevenLabs
  TTS), and the trader confirms by voice or tap.
- **Why voice-first**: matches literacy levels and typing speed on cheap Android phones, and
  mirrors how traders already talk to customers about a sale.
- **Why ElevenLabs + Claude**: multilingual/code-switched STT+TTS quality for Kiswahili/Sheng/
  English mixing; Claude's structured extraction from messy, mixed-language speech.
- **Demo script**: a 60-90 second walkthrough judges can watch live (register → speak a sale →
  confirm → see it land in the ledger).
- **Roadmap** (qualitative only, no invented numbers): M-Pesa integration, SMS fallback for
  feature phones, credit-scoring from ledger history.

Constraint: no fabricated market-size or user statistics. Where a number would strengthen a
claim, mark it `[cite: your own figure]` rather than inventing one.

## Testing

- Frontend: `npm run build` must stay clean after the refactor; manually exercise auth, record →
  confirm → ledger flow in a browser (mic permission grant and deny paths).
- No backend test changes needed (no backend changes in scope).
- No automated tests added for the pitch doc (not code).
