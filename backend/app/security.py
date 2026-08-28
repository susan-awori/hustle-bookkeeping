from __future__ import annotations

import hashlib
import hmac
import re
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from app.config import get_settings

PHONE_RE = re.compile(r"^\+254[17]\d{8}$")
PIN_RE = re.compile(r"^\d{4,6}$")


def normalize_ke_phone(raw: str) -> str:
    digits = re.sub(r"\D", "", raw.strip())
    if digits.startswith("254") and len(digits) == 12:
        candidate = f"+{digits}"
    elif digits.startswith("0") and len(digits) == 10:
        candidate = f"+254{digits[1:]}"
    elif len(digits) == 9 and digits[0] in "17":
        candidate = f"+254{digits}"
    else:
        candidate = f"+{digits}"
    if not PHONE_RE.match(candidate):
        raise ValueError("Phone must be a Kenyan mobile number (+2547… or +2541…)")
    return candidate


def hash_phone(phone: str) -> str:
    settings = get_settings()
    normalized = normalize_ke_phone(phone)
    return hmac.new(
        settings.phone_hash_pepper.encode("utf-8"),
        normalized.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def hash_pin(pin: str) -> str:
    if not PIN_RE.match(pin):
        raise ValueError("PIN must be 4 to 6 digits")
    return bcrypt.hashpw(pin.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_pin(pin: str, pin_hash: str) -> bool:
    if not PIN_RE.match(pin):
        return False
    return bcrypt.checkpw(pin.encode("utf-8"), pin_hash.encode("utf-8"))


def _encode(payload: dict) -> str:
    settings = get_settings()
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_access_token(trader_id: uuid.UUID) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    return _encode(
        {
            "sub": str(trader_id),
            "type": "access",
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(minutes=settings.access_token_minutes)).timestamp()),
        }
    )


def create_refresh_token(trader_id: uuid.UUID) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    return _encode(
        {
            "sub": str(trader_id),
            "type": "refresh",
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(days=settings.refresh_token_days)).timestamp()),
        }
    )


def decode_token(token: str, expected_type: str) -> uuid.UUID:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise ValueError("Invalid token") from exc
    if payload.get("type") != expected_type or not payload.get("sub"):
        raise ValueError("Invalid token")
    return uuid.UUID(payload["sub"])
