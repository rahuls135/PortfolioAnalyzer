"""add portfolio analysis cache fields

Revision ID: 0002_portfolio_analysis_cache
Revises: 0001_initial_schema
Create Date: 2025-02-09 00:00:01.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0002_portfolio_analysis_cache"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("user_profiles", sa.Column("portfolio_analysis", sa.String(), nullable=True))
    op.add_column("user_profiles", sa.Column("portfolio_analysis_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("user_profiles", "portfolio_analysis_at")
    op.drop_column("user_profiles", "portfolio_analysis")
