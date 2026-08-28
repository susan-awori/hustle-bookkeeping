from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models import EntryType
from app.security import PIN_RE, normalize_ke_phone


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class RegisterRequest(StrictModel):
    phone_number: str
    pin: str
    display_name: str = Field(min_length=1, max_length=120)

    @field_validator("phone_number")
    @classmethod
    def valid_phone(cls, value: str) -> str:
        return normalize_ke_phone(value)

    @field_validator("pin")
    @classmethod
    def valid_pin(cls, value: str) -> str:
        if not PIN_RE.match(value):
            raise ValueError("PIN must be 4 to 6 digits")
        return value


class LoginRequest(StrictModel):
    phone_number: str
    pin: str

    @field_validator("phone_number")
    @classmethod
    def valid_phone(cls, value: str) -> str:
        return normalize_ke_phone(value)

    @field_validator("pin")
    @classmethod
    def valid_pin(cls, value: str) -> str:
        if not PIN_RE.match(value):
            raise ValueError("PIN must be 4 to 6 digits")
        return value


class RefreshRequest(StrictModel):
    refresh_token: str = Field(min_length=20)


class TokenResponse(StrictModel):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int = 900


class TraderPublic(StrictModel):
    id: UUID
    display_name: str
    save_voice_notes: bool
    created_at: datetime
    model_config = ConfigDict(extra="forbid", from_attributes=True)


class VoiceParseQuery(StrictModel):
    save_voice_notes: bool = False


class ParsedEntry(StrictModel):
    entry_type: EntryType
    item_description: str = Field(min_length=1, max_length=255)
    amount_kes: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    counterparty_name: str | None = Field(default=None, max_length=120)
    is_settled: bool = True


class VoiceParseResponse(StrictModel):
    transcript: str
    entries: list[ParsedEntry]
    confirmation_text: str
    confirmation_audio_base64: str
    audio_mime_type: str = "audio/mpeg"
    needs_clarification: bool = False


class ConfirmLedgerRequest(StrictModel):
    transcript: str = Field(min_length=1, max_length=4000)
    entries: list[ParsedEntry] = Field(min_length=1, max_length=20)


class LedgerEntryPublic(StrictModel):
    id: UUID
    trader_id: UUID
    entry_type: EntryType
    item_description: str
    amount_kes: Decimal
    counterparty_name: str | None
    is_settled: bool
    created_at: datetime
    model_config = ConfigDict(extra="forbid", from_attributes=True)


class LedgerListResponse(StrictModel):
    items: list[LedgerEntryPublic]
    total: int


class PreferenceRequest(StrictModel):
    save_voice_notes: bool
