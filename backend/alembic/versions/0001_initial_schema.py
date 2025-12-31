"""initial schema

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2025-02-09 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("supabase_user_id", sa.String(), nullable=True),
        sa.Column("age", sa.Integer(), nullable=True),
        sa.Column("income", sa.Float(), nullable=True),
        sa.Column("risk_tolerance", sa.String(), nullable=True),
        sa.Column("retirement_years", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_users_supabase_user_id", "users", ["supabase_user_id"], unique=True)

    op.create_table(
        "stock_data",
        sa.Column("ticker", sa.String(), primary_key=True),
        sa.Column("current_price", sa.Float(), nullable=True),
        sa.Column("pe_ratio", sa.Float(), nullable=True),
        sa.Column("sector", sa.String(), nullable=True),
        sa.Column("market_cap", sa.Float(), nullable=True),
        sa.Column("last_updated", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_stock_data_ticker", "stock_data", ["ticker"])

    op.create_table(
        "news_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ticker", sa.String(), nullable=True),
        sa.Column("headline", sa.String(), nullable=True),
        sa.Column("url", sa.String(), nullable=True),
        sa.Column("published_date", sa.DateTime(), nullable=True),
        sa.Column("ai_summary", sa.String(), nullable=True),
        sa.Column("sentiment", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_news_items_ticker", "news_items", ["ticker"])

    op.create_table(
        "holdings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("ticker", sa.String(), nullable=True),
        sa.Column("shares", sa.Float(), nullable=True),
        sa.Column("avg_price", sa.Float(), nullable=True),
        sa.UniqueConstraint("user_id", "ticker", name="uq_holdings_user_ticker"),
    )
    op.create_index("ix_holdings_ticker", "holdings", ["ticker"])

    op.create_table(
        "user_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("recommended_equity_pct", sa.Float(), nullable=True),
        sa.Column("recommended_allocation", sa.JSON(), nullable=True),
        sa.Column("ai_analysis", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("user_profiles")
    op.drop_index("ix_holdings_ticker", table_name="holdings")
    op.drop_table("holdings")
    op.drop_index("ix_news_items_ticker", table_name="news_items")
    op.drop_table("news_items")
    op.drop_index("ix_stock_data_ticker", table_name="stock_data")
    op.drop_table("stock_data")
    op.drop_index("ix_users_supabase_user_id", table_name="users")
    op.drop_table("users")
