"""cache summaries by requested length

Revision ID: 0005_summary_length_cache
Revises: 0004_document_insights
Create Date: 2026-07-18
"""

from alembic import op
import sqlalchemy as sa

revision = "0005_summary_length_cache"
down_revision = "0004_document_insights"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index(op.f("ix_document_insights_document_id"), table_name="document_insights")
    with op.batch_alter_table("document_insights") as batch_op:
        batch_op.add_column(sa.Column("summary_length", sa.String(length=20), server_default="standard", nullable=False))
        batch_op.add_column(sa.Column("document_type", sa.String(length=80), server_default="document", nullable=False))
        batch_op.create_unique_constraint("uq_document_insights_document_length", ["document_id", "summary_length"])
    op.create_index(op.f("ix_document_insights_document_id"), "document_insights", ["document_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_document_insights_document_id"), table_name="document_insights")
    with op.batch_alter_table("document_insights") as batch_op:
        batch_op.drop_constraint("uq_document_insights_document_length", type_="unique")
        batch_op.drop_column("document_type")
        batch_op.drop_column("summary_length")
    op.create_index(op.f("ix_document_insights_document_id"), "document_insights", ["document_id"], unique=True)
