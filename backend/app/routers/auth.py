from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.deps import get_current_trader
from app.logging_policy import get_logger, hash_trader_id
from app.models import Trader
from app.rate_limit import limiter
from app.repositories import traders as traders_repo
from app.schemas import (
    LoginRequest,
    PreferenceRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    TraderPublic,
)
from app.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_phone,
    hash_pin,
    verify_pin,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
logger = get_logger()


def _tokens(trader: Trader) -> TokenResponse:
    settings = get_settings()
    return TokenResponse(
        access_token=create_access_token(trader.id),
        refresh_token=create_refresh_token(trader.id),
        expires_in=settings.access_token_minutes * 60,
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
def register(request: Request, payload: RegisterRequest, db: Session = Depends(get_db)) -> TokenResponse:
    phone_hash = hash_phone(payload.phone_number)
    if traders_repo.get_by_phone_hash(db, phone_hash):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Account already exists")
    trader = traders_repo.create_trader(
        db,
        phone_hash=phone_hash,
        display_name=payload.display_name,
        pin_hash=hash_pin(payload.pin),
    )
    logger.info("trader_registered", trader_id_hash=hash_trader_id(str(trader.id), get_settings().phone_hash_pepper))
    return _tokens(trader)


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
def login(request: Request, payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    phone_hash = hash_phone(payload.phone_number)
    trader = traders_repo.get_by_phone_hash(db, phone_hash)
    if trader is None or not verify_pin(payload.pin, trader.pin_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Wrong phone or PIN")
    logger.info("trader_login", trader_id_hash=hash_trader_id(str(trader.id), get_settings().phone_hash_pepper))
    return _tokens(trader)


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("20/minute")
def refresh(request: Request, payload: RefreshRequest, db: Session = Depends(get_db)) -> TokenResponse:
    try:
        trader_id = decode_token(payload.refresh_token, expected_type="refresh")
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    trader = traders_repo.get_by_id(db, trader_id)
    if trader is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    return _tokens(trader)


@router.get("/me", response_model=TraderPublic)
def me(trader: Trader = Depends(get_current_trader)) -> Trader:
    return trader


@router.patch("/me", response_model=TraderPublic)
def update_me(
    payload: PreferenceRequest,
    trader: Trader = Depends(get_current_trader),
    db: Session = Depends(get_db),
) -> Trader:
    updated = traders_repo.update_voice_preference(db, trader.id, payload.save_voice_notes)
    assert updated is not None
    return updated
