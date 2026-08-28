"""Trader queries.

TENANCY: Lookups that return a trader for an authenticated session always
use the trader_id from the verified JWT (or the HMAC of the phone supplied
at login/register). No function here lists traders without a unique key.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Trader


def get_by_id(db: Session, trader_id: uuid.UUID) -> Trader | None:
    # TENANCY: keyed by primary key from the authenticated token, not a client-supplied filter.
    return db.get(Trader, trader_id)


def get_by_phone_hash(db: Session, phone_hash: str) -> Trader | None:
    # TENANCY: unique hashed phone from the login/register payload; not a ledger dump.
    return db.scalar(select(Trader).where(Trader.phone_number == phone_hash))


def create_trader(
    db: Session,
    *,
    phone_hash: str,
    display_name: str,
    pin_hash: str,
) -> Trader:
    trader = Trader(phone_number=phone_hash, display_name=display_name, pin_hash=pin_hash)
    db.add(trader)
    db.commit()
    db.refresh(trader)
    return trader


def update_voice_preference(db: Session, trader_id: uuid.UUID, save_voice_notes: bool) -> Trader | None:
    # TENANCY: update only the authenticated trader_id.
    trader = get_by_id(db, trader_id)
    if trader is None:
        return None
    trader.save_voice_notes = save_voice_notes
    db.commit()
    db.refresh(trader)
    return trader
