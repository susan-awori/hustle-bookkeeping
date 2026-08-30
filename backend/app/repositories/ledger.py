"""Ledger queries.

TENANCY: There is NO query in this module that fetches ledger data without a
trader_id filter tied to the authenticated session. Callers must pass the
trader_id from the verified JWT — never from an untrusted body field used as
the sole scope.
"""

from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import EntryType, LedgerEntry, PaymentMethod


def list_for_trader(
    db: Session,
    trader_id: uuid.UUID,
    *,
    limit: int = 100,
    offset: int = 0,
) -> tuple[list[LedgerEntry], int]:
    # TENANCY: WHERE ledger_entries.trader_id = authenticated trader_id.
    filters = LedgerEntry.trader_id == trader_id
    total = db.scalar(select(func.count()).select_from(LedgerEntry).where(filters)) or 0
    items = list(
        db.scalars(
            select(LedgerEntry)
            .where(filters)
            .order_by(LedgerEntry.created_at.desc())
            .limit(limit)
            .offset(offset)
        ).all()
    )
    return items, int(total)


def insert_entry(
    db: Session,
    *,
    trader_id: uuid.UUID,
    entry_type: EntryType,
    item_description: str,
    amount_kes: Decimal,
    counterparty_name: str | None,
    payment_method: PaymentMethod,
    is_settled: bool,
    raw_transcript: str,
) -> LedgerEntry:
    # TENANCY: row is always inserted with the authenticated trader_id.
    row = LedgerEntry(
        trader_id=trader_id,
        entry_type=entry_type,
        item_description=item_description,
        amount_kes=amount_kes,
        counterparty_name=counterparty_name,
        payment_method=payment_method,
        is_settled=is_settled,
        raw_transcript=raw_transcript,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_outstanding_credit(db: Session, trader_id: uuid.UUID) -> list[LedgerEntry]:
    # TENANCY: only unsettled credit for the authenticated trader.
    return list(
        db.scalars(
            select(LedgerEntry)
            .where(
                LedgerEntry.trader_id == trader_id,
                LedgerEntry.entry_type == EntryType.credit_given,
                LedgerEntry.is_settled.is_(False),
            )
            .order_by(LedgerEntry.created_at.desc())
        ).all()
    )


def repay_credit(
    db: Session,
    *,
    trader_id: uuid.UUID,
    entry_id: uuid.UUID,
    payment_method: PaymentMethod,
    raw_transcript: str,
) -> tuple[LedgerEntry, LedgerEntry] | None:
    credit_row = get_for_trader(db, trader_id, entry_id)
    if credit_row is None or credit_row.entry_type is not EntryType.credit_given or credit_row.is_settled:
        return None
    credit_row.is_settled = True
    repayment = LedgerEntry(
        trader_id=trader_id,
        entry_type=EntryType.credit_repaid,
        item_description=credit_row.item_description,
        amount_kes=credit_row.amount_kes,
        counterparty_name=credit_row.counterparty_name,
        payment_method=payment_method,
        is_settled=True,
        raw_transcript=raw_transcript,
    )
    db.add(repayment)
    db.commit()
    db.refresh(credit_row)
    db.refresh(repayment)
    return credit_row, repayment


def get_for_trader(db: Session, trader_id: uuid.UUID, entry_id: uuid.UUID) -> LedgerEntry | None:
    # TENANCY: both primary key AND trader_id from the session must match.
    return db.scalar(
        select(LedgerEntry).where(LedgerEntry.id == entry_id, LedgerEntry.trader_id == trader_id)
    )
