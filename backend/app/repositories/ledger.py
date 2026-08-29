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

from app.models import EntryType, LedgerEntry


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
        is_settled=is_settled,
        raw_transcript=raw_transcript,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_for_trader(db: Session, trader_id: uuid.UUID, entry_id: uuid.UUID) -> LedgerEntry | None:
    # TENANCY: both primary key AND trader_id from the session must match.
    return db.scalar(
        select(LedgerEntry).where(LedgerEntry.id == entry_id, LedgerEntry.trader_id == trader_id)
    )


def update_entry(
    db: Session,
    *,
    trader_id: uuid.UUID,
    entry_id: uuid.UUID,
    entry_type: EntryType | None = None,
    item_description: str | None = None,
    amount_kes: Decimal | None = None,
    counterparty_name: str | None = None,
    is_settled: bool | None = None,
) -> LedgerEntry | None:
    # TENANCY: lookup requires both entry_id and authenticated trader_id.
    row = get_for_trader(db, trader_id, entry_id)
    if row is None:
        return None
    if entry_type is not None:
        row.entry_type = entry_type
    if item_description is not None:
        row.item_description = item_description
    if amount_kes is not None:
        row.amount_kes = amount_kes
    if counterparty_name is not None:
        row.counterparty_name = counterparty_name
    if is_settled is not None:
        row.is_settled = is_settled
    db.commit()
    db.refresh(row)
    return row


def delete_entry(db: Session, *, trader_id: uuid.UUID, entry_id: uuid.UUID) -> bool:
    # TENANCY: lookup requires both entry_id and authenticated trader_id.
    row = get_for_trader(db, trader_id, entry_id)
    if row is None:
        return False
    db.delete(row)
    db.commit()
    return True


def get_stats_for_trader(db: Session, trader_id: uuid.UUID) -> dict[str, Decimal | int]:
    # TENANCY: WHERE ledger_entries.trader_id = authenticated trader_id.
    rows = list(
        db.scalars(
            select(LedgerEntry).where(LedgerEntry.trader_id == trader_id)
        ).all()
    )
    total_sales = Decimal("0.00")
    total_expenses = Decimal("0.00")
    total_credit_given = Decimal("0.00")
    total_credit_repaid = Decimal("0.00")
    outstanding_debt = Decimal("0.00")

    for r in rows:
        amt = Decimal(str(r.amount_kes))
        if r.entry_type == EntryType.sale:
            total_sales += amt
        elif r.entry_type == EntryType.expense:
            total_expenses += amt
        elif r.entry_type == EntryType.credit_given:
            total_credit_given += amt
            if not r.is_settled:
                outstanding_debt += amt
        elif r.entry_type == EntryType.credit_repaid:
            total_credit_repaid += amt

    net_cash_flow = total_sales + total_credit_repaid - total_expenses

    return {
        "total_sales": total_sales,
        "total_expenses": total_expenses,
        "total_credit_given": total_credit_given,
        "total_credit_repaid": total_credit_repaid,
        "outstanding_debt": outstanding_debt,
        "net_cash_flow": net_cash_flow,
        "total_entries": len(rows),
    }
