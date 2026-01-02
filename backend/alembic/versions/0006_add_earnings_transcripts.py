"""add earnings transcripts

Revision ID: 0006_add_earnings_transcripts
Revises: 0005_unique_user_profile
Create Date: 2025-02-10 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0006_add_earnings_transcripts"
down_revision = "0005_unique_user_profile"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "earnings_transcripts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ticker", sa.String(), nullable=True),
        sa.Column("quarter", sa.String(), nullable=True),
        sa.Column("transcript", sa.String(), nullable=True),
        sa.Column("summary", sa.String(), nullable=True),
        sa.Column("fetched_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_earnings_transcripts_ticker", "earnings_transcripts", ["ticker"])
    op.create_index("ix_earnings_transcripts_quarter", "earnings_transcripts", ["quarter"])
    op.create_unique_constraint("uq_earnings_ticker_quarter", "earnings_transcripts", ["ticker", "quarter"])


def downgrade() -> None:
    op.drop_constraint("uq_earnings_ticker_quarter", "earnings_transcripts", type_="unique")
    op.drop_index("ix_earnings_transcripts_quarter", table_name="earnings_transcripts")
    op.drop_index("ix_earnings_transcripts_ticker", table_name="earnings_transcripts")
    op.drop_table("earnings_transcripts")
