"""merge heads for user risk fields and analysis cache

Revision ID: 0003_merge_heads
Revises: 0002_add_user_risk_fields, 0002_portfolio_analysis_cache
Create Date: 2025-02-10 00:00:00.000000

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "0003_merge_heads"
down_revision = ("0002_add_user_risk_fields", "0002_portfolio_analysis_cache")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
