"""seed_document_tool

Revision ID: e8f2a6b4c1d9
Revises: c7d1e5a93f20
Create Date: 2026-10-22 10:05:00.000000

"""

from alembic import op
import sqlalchemy as sa

revision = "e8f2a6b4c1d9"
down_revision = "c7d1e5a93f20"
branch_labels = None
depends_on = None


DOCUMENT_TOOL = {
    "name": "document",
    "display_name": "Document",
    "description": (
        "Create, read and edit a Markdown document that the user can open "
        "and edit in a side panel."
    ),
    "in_code_tool_id": "DocumentTool",
    "enabled": True,
}


def upgrade() -> None:
    conn = op.get_bind()
    existing = conn.execute(
        sa.text("SELECT 1 FROM tool WHERE in_code_tool_id = :in_code_tool_id"),
        {"in_code_tool_id": DOCUMENT_TOOL["in_code_tool_id"]},
    ).fetchone()
    if existing:
        return
    conn.execute(
        sa.text("""
            INSERT INTO tool (name, display_name, description, in_code_tool_id, enabled)
            VALUES (:name, :display_name, :description, :in_code_tool_id, :enabled)
            """),
        DOCUMENT_TOOL,
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text("DELETE FROM tool WHERE in_code_tool_id = :in_code_tool_id"),
        {"in_code_tool_id": DOCUMENT_TOOL["in_code_tool_id"]},
    )
