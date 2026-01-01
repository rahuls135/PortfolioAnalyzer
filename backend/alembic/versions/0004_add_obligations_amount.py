"""add obligations amount to users

Revision ID: 0004_add_obligations_amount
Revises: 0003_merge_heads
Create Date: 2025-02-10 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0004_add_obligations_amount"
down_revision = "0003_merge_heads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("obligations_amount", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "obligations_amount")
