"""add cached analysis metrics and transcripts

Revision ID: 0008_add_profile_analysis_cache
Revises: 0007_add_asset_type
Create Date: 2025-02-10 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0008_add_profile_analysis_cache"
down_revision = "0007_add_asset_type"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("user_profiles", sa.Column("portfolio_metrics", sa.JSON(), nullable=True))
    op.add_column("user_profiles", sa.Column("portfolio_transcripts", sa.JSON(), nullable=True))
    op.add_column("user_profiles", sa.Column("portfolio_transcripts_quarter", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("user_profiles", "portfolio_transcripts_quarter")
    op.drop_column("user_profiles", "portfolio_transcripts")
    op.drop_column("user_profiles", "portfolio_metrics")
