"""add user obligations and risk assessment mode

Revision ID: 0002_add_user_risk_fields
Revises: 0001_initial_schema
Create Date: 2025-02-10 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0002_add_user_risk_fields"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("risk_assessment_mode", sa.String(), nullable=True))
    op.add_column("users", sa.Column("obligations", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "obligations")
    op.drop_column("users", "risk_assessment_mode")
