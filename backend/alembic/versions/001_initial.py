"""initial hustle schema

Revision ID: 001_initial
Revises:
Create Date: 2026-08-28

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "traders",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("phone_number", sa.String(length=64), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("pin_hash", sa.String(length=128), nullable=False),
        sa.Column("save_voice_notes", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("phone_number"),
    )
    op.create_index("ix_traders_phone_number", "traders", ["phone_number"], unique=True)

    op.create_table(
        "ledger_entries",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("trader_id", sa.String(length=36), nullable=False),
        sa.Column("entry_type", sa.String(length=32), nullable=False),
        sa.Column("item_description", sa.String(length=255), nullable=False),
        sa.Column("amount_kes", sa.Numeric(14, 2), nullable=False),
        sa.Column("counterparty_name", sa.String(length=120), nullable=True),
        sa.Column("is_settled", sa.Boolean(), nullable=False),
        sa.Column("raw_transcript", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint(
            "entry_type IN ('sale', 'expense', 'credit_given', 'credit_repaid')",
            name="ck_ledger_entry_type",
        ),
        sa.ForeignKeyConstraint(["trader_id"], ["traders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ledger_entries_trader_id", "ledger_entries", ["trader_id"])

    op.create_table(
        "audio_logs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("trader_id", sa.String(length=36), nullable=False),
        sa.Column("s3_or_storage_path", sa.String(length=512), nullable=True),
        sa.Column("transcript", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["trader_id"], ["traders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audio_logs_trader_id", "audio_logs", ["trader_id"])
    op.create_index("ix_audio_logs_expires_at", "audio_logs", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_audio_logs_expires_at", table_name="audio_logs")
    op.drop_index("ix_audio_logs_trader_id", table_name="audio_logs")
    op.drop_table("audio_logs")
    op.drop_index("ix_ledger_entries_trader_id", table_name="ledger_entries")
    op.drop_table("ledger_entries")
    op.drop_index("ix_traders_phone_number", table_name="traders")
    op.drop_table("traders")
