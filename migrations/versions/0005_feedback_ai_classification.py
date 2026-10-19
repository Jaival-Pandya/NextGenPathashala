"""Store AI-assigned feedback categories.

Revision ID: 0005_feedback_ai_classification
Revises: 0004_classroom_assessments
Create Date: 2026-10-16
"""
from alembic import op
import sqlalchemy as sa

revision = "0005_feedback_ai_classification"
down_revision = "0004_classroom_assessments"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("user_feedback", sa.Column("ai_category", sa.String(length=40), nullable=True))
    op.add_column("user_feedback", sa.Column("ai_categorized_at", sa.DateTime(), nullable=True))


def downgrade():
    op.drop_column("user_feedback", "ai_categorized_at")
    op.drop_column("user_feedback", "ai_category")