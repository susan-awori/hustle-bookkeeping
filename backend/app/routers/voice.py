from __future__ import annotations

import base64

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.deps import get_current_trader
from app.logging_policy import get_logger, hash_trader_id
from app.models import EntryType, Trader
from app.rate_limit import limiter
from app.repositories import ledger as ledger_repo
from app.schemas import (
    ConfirmLedgerRequest,
    LedgerEntryPublic,
    ParseTextRequest,
    TranslateRequest,
    TranslateResponse,
    TranscribeResponse,
    VoiceParseResponse,
)
from app.services.audio_store import persist_opt_in_audio
from app.services.elevenlabs import ALLOWED_AUDIO_TYPES, ElevenLabsError, synthesize_speech, transcribe_audio
from app.services.llm_parser import ParseError, parse_transcript, translate_to_english

router = APIRouter(prefix="/api/v1/voice", tags=["voice"])
logger = get_logger()

MAX_AUDIO_BYTES = 5 * 1024 * 1024


def _elevenlabs_configured() -> bool:
    key = get_settings().elevenlabs_api_key.strip()
    return bool(key) and not key.startswith("test-")


async def _resolve_transcript(
    audio_bytes: bytes,
    content_type: str,
    filename: str,
    browser_transcript: str | None,
) -> str:
    settings = get_settings()
    if _elevenlabs_configured():
        try:
            return transcribe_audio(audio_bytes, content_type, filename)
        except ElevenLabsError as exc:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    if settings.environment == "development" and browser_transcript and browser_transcript.strip():
        return browser_transcript.strip()
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=(
            "Voice transcription is not configured. Add ELEVENLABS_API_KEY to backend/.env, "
            "or use Chrome/Edge so the browser can capture your speech as text."
        ),
    )


def _voice_parse_response(transcript: str, *, save_voice_notes: bool, trader: Trader) -> VoiceParseResponse:
    settings = get_settings()
    try:
        entries, confirmation_text, needs = parse_transcript(transcript)
    except ParseError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    audio_b64 = ""
    if _elevenlabs_configured():
        try:
            tts = synthesize_speech(confirmation_text)
            audio_b64 = base64.b64encode(tts).decode("ascii")
        except ElevenLabsError as exc:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    logger.info(
        "voice_parsed",
        trader_id_hash=hash_trader_id(str(trader.id), settings.phone_hash_pepper),
        entry_type=entries[0].entry_type.value if entries else "none",
        entry_count=len(entries),
        save_voice_notes=save_voice_notes,
    )
    return VoiceParseResponse(
        transcript=transcript,
        entries=entries,
        confirmation_text=confirmation_text,
        confirmation_audio_base64=audio_b64,
        needs_clarification=needs,
    )


@router.post("/translate", response_model=TranslateResponse)
@limiter.limit("20/minute")
def translate_text(
    request: Request,
    payload: TranslateRequest,
    _trader: Trader = Depends(get_current_trader),
) -> TranslateResponse:
    try:
        return TranslateResponse(translation=translate_to_english(payload.text))
    except ParseError:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Could not translate text")


@router.post("/transcribe", response_model=TranscribeResponse)
@limiter.limit("15/minute")
async def transcribe_voice(
    request: Request,
    audio: UploadFile = File(...),
    browser_transcript: str | None = Form(None),
    _trader: Trader = Depends(get_current_trader),
) -> TranscribeResponse:
    content_type = (audio.content_type or "application/octet-stream").lower()
    if not any(content_type.startswith(allowed.split(";")[0]) for allowed in ALLOWED_AUDIO_TYPES):
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Unsupported audio type")
    audio_bytes = await audio.read()
    try:
        if not audio_bytes or len(audio_bytes) > MAX_AUDIO_BYTES:
            raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Audio too large or empty")
        transcript = await _resolve_transcript(
            audio_bytes,
            content_type,
            audio.filename or "take.webm",
            browser_transcript,
        )
    finally:
        del audio_bytes
    return TranscribeResponse(transcript=transcript)


@router.post("/parse-text", response_model=VoiceParseResponse)
@limiter.limit("20/minute")
def parse_text(
    request: Request,
    payload: ParseTextRequest,
    trader: Trader = Depends(get_current_trader),
) -> VoiceParseResponse:
    return _voice_parse_response(payload.text, save_voice_notes=False, trader=trader)


@router.post("/parse", response_model=VoiceParseResponse)
@limiter.limit("10/minute")
async def parse_voice(
    request: Request,
    audio: UploadFile = File(...),
    save_voice_notes: bool = Form(False),
    browser_transcript: str | None = Form(None),
    trader: Trader = Depends(get_current_trader),
    db: Session = Depends(get_db),
) -> VoiceParseResponse:
    content_type = (audio.content_type or "application/octet-stream").lower()
    if not any(content_type.startswith(allowed.split(";")[0]) for allowed in ALLOWED_AUDIO_TYPES):
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Unsupported audio type")
    audio_bytes = await audio.read()
    try:
        if not audio_bytes or len(audio_bytes) > MAX_AUDIO_BYTES:
            raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Audio too large or empty")
        transcript = await _resolve_transcript(
            audio_bytes,
            content_type,
            audio.filename or "take.webm",
            browser_transcript,
        )
        persist = save_voice_notes or trader.save_voice_notes
        if persist:
            persist_opt_in_audio(db, trader_id=trader.id, transcript=transcript, audio_bytes=audio_bytes)
    finally:
        del audio_bytes

    return _voice_parse_response(transcript, save_voice_notes=persist, trader=trader)


@router.post("/confirm", response_model=list[LedgerEntryPublic])
@limiter.limit("30/minute")
def confirm_entries(
    request: Request,
    payload: ConfirmLedgerRequest,
    trader: Trader = Depends(get_current_trader),
    db: Session = Depends(get_db),
) -> list[LedgerEntryPublic]:
    stored = []
    for entry in payload.entries:
        row = ledger_repo.insert_entry(
            db,
            trader_id=trader.id,
            entry_type=entry.entry_type,
            item_description=entry.item_description,
            amount_kes=entry.amount_kes,
            counterparty_name=entry.counterparty_name,
            payment_method=entry.payment_method,
            is_settled=False if entry.entry_type is EntryType.credit_given else entry.is_settled,
            raw_transcript=payload.transcript,
        )
        stored.append(row)
    logger.info(
        "ledger_confirmed",
        trader_id_hash=hash_trader_id(str(trader.id), get_settings().phone_hash_pepper),
        entry_count=len(stored),
        entry_type=stored[0].entry_type.value if stored else "none",
    )
    return stored
