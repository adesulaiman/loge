"""add chat_document and chat_document_version

Revision ID: c7d1e5a93f20
Revises: d7e4f2a91b03
Create Date: 2026-10-22 10:00:00.000000

Versioned Markdown documents that the agent and the user edit in turn.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "c7d1e5a93f20"
down_revision = "d7e4f2a91b03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "chat_document",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("user.id"),
            nullable=False,
        ),
        sa.Column("chat_session_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("current_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_chat_document_user_id", "chat_document", ["user_id"])
    op.create_index(
        "ix_chat_document_chat_session_id", "chat_document", ["chat_session_id"]
    )
    op.create_table(
        "chat_document_version",
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("chat_document.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("version", sa.Integer(), primary_key=True),
        sa.Column("content_md", sa.Text(), nullable=False),
        sa.Column("author", sa.String(), nullable=False),
        sa.Column("summary", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("chat_document_version")
    op.drop_index("ix_chat_document_chat_session_id", table_name="chat_document")
    op.drop_index("ix_chat_document_user_id", table_name="chat_document")
    op.drop_table("chat_document")
