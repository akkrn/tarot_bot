"""rename balance column to free_attempts and add balance_rub column

Revision ID: 3d18c13b9f0e
Revises: 81521565f790
Create Date: 2025-06-05 12:35:14.493965
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "3d18c13b9f0e"
down_revision: Union[str, None] = "81521565f790"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("users", "balance", new_column_name="free_attempts")
    op.add_column("users", sa.Column("balance_rub", sa.BigInteger(), nullable=False, server_default="0"))
    op.alter_column("users", "balance_rub", server_default=None)  


def downgrade() -> None:
    op.alter_column("users", "free_attempts", new_column_name="balance")
    op.drop_column("users", "balance_rub")
