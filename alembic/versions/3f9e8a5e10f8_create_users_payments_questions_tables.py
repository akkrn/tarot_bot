"""Create users,payments,questions tables

Revision ID: 3f9e8a5e10f8
Revises: 
Create Date: 2024-07-28 18:35:42.577592

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "3f9e8a5e10f8"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_tg_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(), nullable=True),
        sa.Column("first_name", sa.String(), nullable=True),
        sa.Column("last_name", sa.String(), nullable=True),
        sa.Column("real_name", sa.String(), nullable=True),
        sa.Column("birth_date", sa.Date(), nullable=True),
        sa.Column("balance", sa.BigInteger(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("ACTIVE", "BANNED", name="userstatus"),
            nullable=False,
        ),
        sa.Column("added_at", sa.TIMESTAMP(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_tg_id"),
    )
    op.create_table(
        "payments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("payment_id", sa.TEXT(), nullable=False),
        sa.Column("invoice_payload", sa.TEXT(), nullable=False),
        sa.Column("total_amount", sa.INTEGER(), nullable=False),
        sa.Column("date", sa.TIMESTAMP(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "questions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("question", sa.TEXT(), nullable=True),
        sa.Column("answer", sa.TEXT(), nullable=True),
        sa.Column("cards", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("added_at", sa.TIMESTAMP(), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table("questions")
    op.drop_table("payments")
    op.drop_table("users")
    # ### end Alembic commands ###
