"""rename processed document status to ready

Revision ID: 0003_ready_document_status
Revises: 0002_refresh_document_metadata
Create Date: 2026-07-11
"""

from alembic import op

revision = "0003_ready_document_status"
down_revision = "0002_refresh_document_metadata"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("UPDATE documents SET status = 'ready' WHERE status = 'processed'")


def downgrade() -> None:
    op.execute("UPDATE documents SET status = 'processed' WHERE status = 'ready'")
