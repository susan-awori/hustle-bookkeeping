from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum as PyEnum

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Text, Uuid, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import Enum as SAEnum


class Base(DeclarativeBase):
    pass


class EntryType(str, PyEnum):
    sale = "sale"
    expense = "expense"
    credit_given = "credit_given"
    credit_repaid = "credit_repaid"


class PaymentMethod(str, PyEnum):
    cash = "cash"
    mpesa = "mpesa"
    credit = "credit"


# native_enum=False keeps SQLite tests working; values still constrained in Postgres via Alembic check.
entry_type_enum = SAEnum(EntryType, name="entry_type", native_enum=False, validate_strings=True)
payment_method_enum = SAEnum(PaymentMethod, name="payment_method", native_enum=False, validate_strings=True)


class Trader(Base):
    __tablename__ = "traders"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    phone_number: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    pin_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    save_voice_notes: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    ledger_entries: Mapped[list["LedgerEntry"]] = relationship(back_populates="trader")
    audio_logs: Mapped[list["AudioLog"]] = relationship(back_populates="trader")


class LedgerEntry(Base):
    __tablename__ = "ledger_entries"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trader_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("traders.id", ondelete="CASCADE"), index=True, nullable=False
    )
    entry_type: Mapped[EntryType] = mapped_column(entry_type_enum, nullable=False)
    item_description: Mapped[str] = mapped_column(String(255), nullable=False)
    amount_kes: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    counterparty_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    payment_method: Mapped[PaymentMethod] = mapped_column(
        payment_method_enum, nullable=False, default=PaymentMethod.cash
    )
    is_settled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    raw_transcript: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    trader: Mapped[Trader] = relationship(back_populates="ledger_entries")


class AudioLog(Base):
    __tablename__ = "audio_logs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trader_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("traders.id", ondelete="CASCADE"), index=True, nullable=False
    )
    s3_or_storage_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    transcript: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    trader: Mapped[Trader] = relationship(back_populates="audio_logs")
