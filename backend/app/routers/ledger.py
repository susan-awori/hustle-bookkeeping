from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_trader
from app.models import Trader
from app.rate_limit import limiter
from app.repositories import ledger as ledger_repo
from app.schemas import CreditOutstandingResponse, LedgerEntryPublic, LedgerListResponse, RepayCreditRequest

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


@router.get("/credit/outstanding", response_model=CreditOutstandingResponse)
@limiter.limit("60/minute")
def list_outstanding_credit(
    request: Request,
    trader: Trader = Depends(get_current_trader),
    db: Session = Depends(get_db),
) -> CreditOutstandingResponse:
    items = ledger_repo.list_outstanding_credit(db, trader.id)
    amount_due = sum((row.amount_kes for row in items), Decimal("0.00"))
    return CreditOutstandingResponse(items=items, total=len(items), amount_due_kes=amount_due)


@router.post("/{entry_id}/repay", response_model=list[LedgerEntryPublic])
@limiter.limit("30/minute")
def repay_credit(
    request: Request,
    entry_id: UUID,
    payload: RepayCreditRequest,
    trader: Trader = Depends(get_current_trader),
    db: Session = Depends(get_db),
) -> list[LedgerEntryPublic]:
    result = ledger_repo.repay_credit(
        db,
        trader_id=trader.id,
        entry_id=entry_id,
        payment_method=payload.payment_method,
        raw_transcript=f"Credit repaid via {payload.payment_method.value}",
    )
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Outstanding credit not found")
    credit_row, repayment = result
    return [credit_row, repayment]


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
