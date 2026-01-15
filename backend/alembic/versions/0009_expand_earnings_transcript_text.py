"""expand earnings transcript text columns

Revision ID: 0009_expand_transcripts
Revises: 0008_add_profile_analysis_cache
Create Date: 2025-01-02
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0009_expand_transcripts"
down_revision = "0008_add_profile_analysis_cache"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "earnings_transcripts",
        "transcript",
        existing_type=sa.String(),
        type_=sa.Text(),
    )
    op.alter_column(
        "earnings_transcripts",
        "summary",
        existing_type=sa.String(),
        type_=sa.Text(),
    )


def downgrade() -> None:
    op.alter_column(
        "earnings_transcripts",
        "summary",
        existing_type=sa.Text(),
        type_=sa.String(),
    )
    op.alter_column(
        "earnings_transcripts",
        "transcript",
        existing_type=sa.Text(),
        type_=sa.String(),
    )
