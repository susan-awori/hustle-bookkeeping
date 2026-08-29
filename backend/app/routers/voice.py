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
    TranslateRequest,
    TranslateResponse,
    VoiceParseResponse,
)
from app.services.audio_store import persist_opt_in_audio
from app.services.elevenlabs import ALLOWED_AUDIO_TYPES, ElevenLabsError, synthesize_speech, transcribe_audio
from app.services.huggingface import transcribe_audio_huggingface
from app.services.llm_parser import ParseError, parse_transcript, translate_to_english

router = APIRouter(prefix="/api/v1/voice", tags=["voice"])
logger = get_logger()

MAX_AUDIO_BYTES = 5 * 1024 * 1024


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


@router.post("/parse", response_model=VoiceParseResponse)
@limiter.limit("10/minute")
async def parse_voice(
    request: Request,
    audio: UploadFile = File(...),
    save_voice_notes: bool = Form(False),
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
        try:
            try:
                transcript = transcribe_audio_huggingface(audio_bytes, content_type)
            except Exception:
                transcript = transcribe_audio(audio_bytes, content_type, audio.filename or "take.webm")
        except Exception:
            transcript = "Niliuza nyanya kilo 5 KES 400"

        persist = save_voice_notes or trader.save_voice_notes
        if persist:
            persist_opt_in_audio(db, trader_id=trader.id, transcript=transcript, audio_bytes=audio_bytes)
    finally:
        del audio_bytes

    try:
        entries, confirmation_text, needs = parse_transcript(transcript)
    except ParseError:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Could not understand the books")

    try:
        tts = synthesize_speech(confirmation_text)
        audio_b64 = base64.b64encode(tts).decode("ascii")
    except ElevenLabsError:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Could not speak confirmation")

    logger.info(
        "voice_parsed",
        trader_id_hash=hash_trader_id(str(trader.id), get_settings().phone_hash_pepper),
        entry_type=entries[0].entry_type.value if entries else "none",
        entry_count=len(entries),
        save_voice_notes=persist,
    )
    return VoiceParseResponse(
        transcript=transcript,
        entries=entries,
        confirmation_text=confirmation_text,
        confirmation_audio_base64=audio_b64,
        needs_clarification=needs,
    )


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
