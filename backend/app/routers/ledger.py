from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_trader
from app.models import Trader
from app.rate_limit import limiter
from app.repositories import ledger as ledger_repo
from app.schemas import (
    CreateLedgerEntryRequest,
    LedgerEntryPublic,
    LedgerListResponse,
    LedgerStatsResponse,
    UpdateLedgerEntryRequest,
)

router = APIRouter(prefix="/api/v1/ledger", tags=["ledger"])


@router.get("", response_model=LedgerListResponse)
@limiter.limit("60/minute")
def list_ledger(
    request: Request,
    trader: Trader = Depends(get_current_trader),
    db: Session = Depends(get_db),
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> LedgerListResponse:
    # TENANCY: trader.id comes from the access token, never from a query parameter.
    items, total = ledger_repo.list_for_trader(db, trader.id, limit=limit, offset=offset)
    return LedgerListResponse(items=list(items), total=total)


@router.get("/stats", response_model=LedgerStatsResponse)
@limiter.limit("60/minute")
def get_stats(
    request: Request,
    trader: Trader = Depends(get_current_trader),
    db: Session = Depends(get_db),
) -> LedgerStatsResponse:
    # TENANCY: stats calculated only for authenticated trader.id.
    stats = ledger_repo.get_stats_for_trader(db, trader.id)
    return LedgerStatsResponse(**stats)


@router.post("", response_model=LedgerEntryPublic, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
def create_manual_entry(
    request: Request,
    payload: CreateLedgerEntryRequest,
    trader: Trader = Depends(get_current_trader),
    db: Session = Depends(get_db),
) -> LedgerEntryPublic:
    # TENANCY: insert entry with authenticated trader.id.
    row = ledger_repo.insert_entry(
        db,
        trader_id=trader.id,
        entry_type=payload.entry_type,
        item_description=payload.item_description,
        amount_kes=payload.amount_kes,
        counterparty_name=payload.counterparty_name,
        is_settled=payload.is_settled,
        raw_transcript="Manual entry",
    )
    return row


@router.get("/{entry_id}", response_model=LedgerEntryPublic)
@limiter.limit("60/minute")
def get_entry(
    request: Request,
    entry_id: UUID,
    trader: Trader = Depends(get_current_trader),
    db: Session = Depends(get_db),
) -> LedgerEntryPublic:
    # TENANCY: lookup requires both entry id and authenticated trader.id.
    row = ledger_repo.get_for_trader(db, trader.id, entry_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return row


@router.patch("/{entry_id}", response_model=LedgerEntryPublic)
@limiter.limit("30/minute")
def update_entry(
    request: Request,
    entry_id: UUID,
    payload: UpdateLedgerEntryRequest,
    trader: Trader = Depends(get_current_trader),
    db: Session = Depends(get_db),
) -> LedgerEntryPublic:
    # TENANCY: update requires entry_id and authenticated trader.id.
    row = ledger_repo.update_entry(
        db,
        trader_id=trader.id,
        entry_id=entry_id,
        entry_type=payload.entry_type,
        item_description=payload.item_description,
        amount_kes=payload.amount_kes,
        counterparty_name=payload.counterparty_name,
        is_settled=payload.is_settled,
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return row


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("30/minute")
def delete_entry(
    request: Request,
    entry_id: UUID,
    trader: Trader = Depends(get_current_trader),
    db: Session = Depends(get_db),
) -> None:
    # TENANCY: delete requires entry_id and authenticated trader.id.
    success = ledger_repo.delete_entry(db, trader_id=trader.id, entry_id=entry_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
