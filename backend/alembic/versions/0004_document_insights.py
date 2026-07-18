"""cache document intelligence summaries

Revision ID: 0004_document_insights
Revises: 0003_ready_document_status
Create Date: 2026-07-18
"""

from alembic import op
import sqlalchemy as sa

revision = "0004_document_insights"
down_revision = "0003_ready_document_status"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "document_insights",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("document_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("overview", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("key_points", sa.JSON(), nullable=False),
        sa.Column("main_sections", sa.JSON(), nullable=False),
        sa.Column("key_entities", sa.JSON(), nullable=False),
        sa.Column("suggested_questions", sa.JSON(), nullable=False),
        sa.Column("sources", sa.JSON(), nullable=False),
        sa.Column("notice", sa.Text(), nullable=True),
        sa.Column("llm_configured", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_document_insights_document_id"), "document_insights", ["document_id"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_document_insights_document_id"), table_name="document_insights")
    op.drop_table("document_insights")
