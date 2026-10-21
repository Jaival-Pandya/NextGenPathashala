"""Add short-lived QR attendance check-ins.

Revision ID: 0006_qr_attendance
Revises: 0005_feedback_ai_classification
Create Date: 2026-10-20
"""
from alembic import op
import sqlalchemy as sa

revision = "0006_qr_attendance"
down_revision = "0005_feedback_ai_classification"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("class_sessions", sa.Column("attendance_qr_token", sa.String(length=64), nullable=True))
    op.add_column("class_sessions", sa.Column("attendance_qr_expires_at", sa.DateTime(), nullable=True))
    op.add_column(
        "attendance_records",
        sa.Column("recorded_via", sa.String(length=20), nullable=False, server_default="manual"),
    )


def downgrade():
    op.drop_column("attendance_records", "recorded_via")
    op.drop_column("class_sessions", "attendance_qr_expires_at")
    op.drop_column("class_sessions", "attendance_qr_token")
