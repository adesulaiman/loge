"""add chat_document_comment

Revision ID: f4a8b2c6d1e3
Revises: e8f2a6b4c1d9
Create Date: 2026-10-22 14:00:00.000000

Comments anchored to quoted text in a chat document, with replies.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "f4a8b2c6d1e3"
down_revision = "e8f2a6b4c1d9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "chat_document_comment",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("chat_document.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "parent_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("chat_document_comment.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("author", sa.String(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("quote", sa.Text(), nullable=False, server_default=""),
        sa.Column("prefix", sa.Text(), nullable=False, server_default=""),
        sa.Column("suffix", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_on_version", sa.Integer(), nullable=False),
        sa.Column(
            "resolved", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_chat_document_comment_document_id", "chat_document_comment", ["document_id"]
    )


def downgrade() -> None:
    op.drop_index(
        "ix_chat_document_comment_document_id", table_name="chat_document_comment"
    )
    op.drop_table("chat_document_comment")
