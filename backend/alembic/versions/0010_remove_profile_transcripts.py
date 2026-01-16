"""remove profile transcript cache columns

Revision ID: 0010_remove_profile_transcripts
Revises: 0009_expand_transcripts
Create Date: 2025-01-02
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0010_remove_profile_transcripts"
down_revision = "0009_expand_transcripts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("user_profiles", "portfolio_transcripts_quarter")
    op.drop_column("user_profiles", "portfolio_transcripts")


def downgrade() -> None:
    op.add_column("user_profiles", sa.Column("portfolio_transcripts", sa.JSON(), nullable=True))
    op.add_column("user_profiles", sa.Column("portfolio_transcripts_quarter", sa.String(), nullable=True))
