"""add user login_locked_at for brute-force lockout

Revision ID: d7e4f2a91b03
Revises: c4d8e2f1a9b3
Create Date: 2026-10-12 09:50:00.000000

Password login lockout after failed attempts. Cleared only by an admin unlock.
"""

from alembic import op
import sqlalchemy as sa

revision = "d7e4f2a91b03"
down_revision = "c4d8e2f1a9b3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user",
        sa.Column(
            "login_locked_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("user", "login_locked_at")
