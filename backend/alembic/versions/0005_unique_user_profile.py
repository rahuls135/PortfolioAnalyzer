"""add unique constraint for user profiles

Revision ID: 0005_unique_user_profile
Revises: 0004_add_obligations_amount
Create Date: 2025-02-10 00:00:00.000000

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "0005_unique_user_profile"
down_revision = "0004_add_obligations_amount"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_unique_constraint("uq_user_profiles_user_id", "user_profiles", ["user_id"])


def downgrade() -> None:
    op.drop_constraint("uq_user_profiles_user_id", "user_profiles", type_="unique")
