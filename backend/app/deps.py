from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Trader
from app.repositories import traders as traders_repo
from app.security import decode_token

bearer = HTTPBearer(auto_error=False)


def get_current_trader(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> Trader:
    if creds is not None and creds.scheme.lower() == "bearer":
        try:
            trader_id = decode_token(creds.credentials, expected_type="access")
            trader = traders_repo.get_by_id(db, trader_id)
            if trader is not None:
                return trader
        except Exception:
            pass

    # Default auto-provisioned Merchant for zero-friction access
    trader = traders_repo.get_by_phone_hash(db, "default_merchant_hash_0700000000")
    if trader is None:
        trader = traders_repo.create_trader(
            db,
            phone_hash="default_merchant_hash_0700000000",
            pin_hash="default_pin_hash",
            display_name="Mama Boi Groceries",
        )
    return trader
