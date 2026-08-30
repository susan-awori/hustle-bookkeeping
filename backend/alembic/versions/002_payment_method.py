"""Add payment_method to ledger entries for cash/mpesa/credit tracking."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002_payment_method"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "ledger_entries",
        sa.Column("payment_method", sa.String(length=16), nullable=False, server_default="cash"),
    )
    op.create_check_constraint(
        "ck_ledger_payment_method",
        "ledger_entries",
        "payment_method IN ('cash', 'mpesa', 'credit')",
    )
    op.execute(
        """
        UPDATE ledger_entries
        SET payment_method = 'credit'
        WHERE entry_type = 'credit_given' AND is_settled = false
        """
    )


def downgrade() -> None:
    op.drop_constraint("ck_ledger_payment_method", "ledger_entries", type_="check")
    op.drop_column("ledger_entries", "payment_method")
