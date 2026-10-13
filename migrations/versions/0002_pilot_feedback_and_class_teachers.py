"""Add explicit class-teacher assignments and tester feedback intake.

Revision ID: 0002_pilot_feedback
Revises: 0001_initial_schema
Create Date: 2026-10-11
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_pilot_feedback"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "class_teachers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("institution_id", sa.Integer(), nullable=False),
        sa.Column("class_id", sa.Integer(), nullable=False),
        sa.Column("teacher_id", sa.Integer(), nullable=False),
        sa.Column("assigned_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["class_id"], ["classes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["teacher_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["assigned_by"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("class_id", "teacher_id", name="uq_teacher_per_class"),
    )
    op.create_index("ix_class_teachers_institution_id", "class_teachers", ["institution_id"])
    op.create_index("ix_class_teachers_class_id", "class_teachers", ["class_id"])
    op.create_index("ix_class_teachers_teacher_id", "class_teachers", ["teacher_id"])

    # Backfill teacher/class relationships for already scheduled sessions.
    # This INSERT...SELECT is supported by PostgreSQL and SQLite.
    op.execute(sa.text("""
        INSERT INTO class_teachers (institution_id, class_id, teacher_id, assigned_by, created_at)
        SELECT institution_id, class_id, teacher_id, MIN(created_by), MIN(created_at)
        FROM class_sessions
        WHERE teacher_id IS NOT NULL AND status != 'cancelled'
        GROUP BY institution_id, class_id, teacher_id
    """))

    op.create_table(
        "pilot_inquiries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("institution_name", sa.String(length=160), nullable=False),
        sa.Column("institution_type", sa.String(length=30), nullable=False),
        sa.Column("role", sa.String(length=40), nullable=False),
        sa.Column("goal", sa.String(length=80), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("consent", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_pilot_inquiries_email", "pilot_inquiries", ["email"])
    op.create_index("ix_pilot_inquiries_status", "pilot_inquiries", ["status"])
    op.create_index("ix_pilot_inquiries_created_at", "pilot_inquiries", ["created_at"])

    op.create_table(
        "user_feedback",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("institution_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("category", sa.String(length=30), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("page", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_user_feedback_institution_id", "user_feedback", ["institution_id"])
    op.create_index("ix_user_feedback_user_id", "user_feedback", ["user_id"])
    op.create_index("ix_user_feedback_status", "user_feedback", ["status"])
    op.create_index("ix_user_feedback_created_at", "user_feedback", ["created_at"])


def downgrade():
    # Remove only the tables and indexes introduced in this revision.
    op.drop_index("ix_user_feedback_created_at", table_name="user_feedback")
    op.drop_index("ix_user_feedback_status", table_name="user_feedback")
    op.drop_index("ix_user_feedback_user_id", table_name="user_feedback")
    op.drop_index("ix_user_feedback_institution_id", table_name="user_feedback")
    op.drop_table("user_feedback")

    op.drop_index("ix_pilot_inquiries_created_at", table_name="pilot_inquiries")
    op.drop_index("ix_pilot_inquiries_status", table_name="pilot_inquiries")
    op.drop_index("ix_pilot_inquiries_email", table_name="pilot_inquiries")
    op.drop_table("pilot_inquiries")

    op.drop_index("ix_class_teachers_teacher_id", table_name="class_teachers")
    op.drop_index("ix_class_teachers_class_id", table_name="class_teachers")
    op.drop_index("ix_class_teachers_institution_id", table_name="class_teachers")
    op.drop_table("class_teachers")
