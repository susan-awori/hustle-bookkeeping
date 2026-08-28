"""Audio log queries.

TENANCY: There is NO query in this module that fetches audio_logs without a
trader_id filter tied to the authenticated session, except the expiry cleanup
job which deletes by expires_at only (no user-data read returned to a client).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AudioLog


def insert_for_trader(
    db: Session,
    *,
    trader_id: uuid.UUID,
    transcript: str,
    s3_or_storage_path: str | None,
    expires_at: datetime,
) -> AudioLog:
    # TENANCY: row is always inserted with the authenticated trader_id.
    row = AudioLog(
        trader_id=trader_id,
        transcript=transcript,
        s3_or_storage_path=s3_or_storage_path,
        expires_at=expires_at,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_expired(db: Session, now: datetime | None = None) -> list[AudioLog]:
    # TENANCY: maintenance job only — returns expired rows for hard delete, not a user-facing read.
    moment = now or datetime.now(timezone.utc)
    return list(db.scalars(select(AudioLog).where(AudioLog.expires_at <= moment)).all())


def hard_delete(db: Session, row: AudioLog) -> None:
    db.delete(row)
    db.commit()
