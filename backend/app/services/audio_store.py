from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import get_settings
from app.logging_policy import get_logger
from app.repositories import audio_logs as audio_repo

logger = get_logger()
VOICE_NOTE_TTL = timedelta(days=30)


def persist_opt_in_audio(
    db: Session,
    *,
    trader_id: uuid.UUID,
    transcript: str,
    audio_bytes: bytes,
) -> None:
    settings = get_settings()
    root = Path(settings.audio_storage_path)
    root.mkdir(parents=True, exist_ok=True)
    filename = f"{trader_id.hex}_{uuid.uuid4().hex}.webm"
    path = root / filename
    path.write_bytes(audio_bytes)
    expires = datetime.now(timezone.utc) + VOICE_NOTE_TTL
    audio_repo.insert_for_trader(
        db,
        trader_id=trader_id,
        transcript=transcript,
        s3_or_storage_path=str(path.resolve()),
        expires_at=expires,
    )


def cleanup_expired_audio(db: Session) -> int:
    rows = audio_repo.list_expired(db)
    count = 0
    for row in rows:
        if row.s3_or_storage_path:
            try:
                os.remove(row.s3_or_storage_path)
            except FileNotFoundError:
                pass
        audio_repo.hard_delete(db, row)
        count += 1
    if count:
        logger.info("expired_audio_deleted", expired_count=count)
    return count
