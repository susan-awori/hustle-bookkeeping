from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_trader
from app.models import Trader
from app.rate_limit import limiter
from app.repositories import ledger as ledger_repo
from app.schemas import LedgerEntryPublic, LedgerListResponse

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
