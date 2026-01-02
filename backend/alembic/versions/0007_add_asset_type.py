"""add asset type to holdings and stock data

Revision ID: 0007_add_asset_type
Revises: 0006_add_earnings_transcripts
Create Date: 2025-02-10 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0007_add_asset_type"
down_revision = "0006_add_earnings_transcripts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("holdings", sa.Column("asset_type", sa.String(), nullable=True))
    op.add_column("stock_data", sa.Column("asset_type", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("stock_data", "asset_type")
    op.drop_column("holdings", "asset_type")
