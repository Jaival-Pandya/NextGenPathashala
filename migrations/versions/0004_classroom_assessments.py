"""Add teacher-created MCQ assessments and single-attempt results.

Revision ID: 0004_classroom_assessments
Revises: 0003_subject_catalog
Create Date: 2026-10-13
"""
from alembic import op
import sqlalchemy as sa

revision = "0004_classroom_assessments"
down_revision = "0003_subject_catalog"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "assessments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("institution_id", sa.Integer(), nullable=False),
        sa.Column("class_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("instructions", sa.Text(), nullable=False),
        sa.Column("questions", sa.JSON(), nullable=False),
        sa.Column("due_at", sa.DateTime(), nullable=True),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["class_id"], ["classes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_assessments_institution_id", "assessments", ["institution_id"])
    op.create_index("ix_assessments_class_id", "assessments", ["class_id"])
    op.create_index("ix_assessments_due_at", "assessments", ["due_at"])
    op.create_index("ix_assessments_is_published", "assessments", ["is_published"])

    op.create_table(
        "assessment_attempts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("assessment_id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("answers", sa.JSON(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("total_questions", sa.Integer(), nullable=False),
        sa.Column("submitted_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["assessment_id"], ["assessments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("assessment_id", "student_id", name="uq_assessment_attempt_per_student"),
    )
    op.create_index("ix_assessment_attempts_assessment_id", "assessment_attempts", ["assessment_id"])
    op.create_index("ix_assessment_attempts_student_id", "assessment_attempts", ["student_id"])


def downgrade():
    op.drop_index("ix_assessment_attempts_student_id", table_name="assessment_attempts")
    op.drop_index("ix_assessment_attempts_assessment_id", table_name="assessment_attempts")
    op.drop_table("assessment_attempts")
    op.drop_index("ix_assessments_is_published", table_name="assessments")
    op.drop_index("ix_assessments_due_at", table_name="assessments")
    op.drop_index("ix_assessments_class_id", table_name="assessments")
    op.drop_index("ix_assessments_institution_id", table_name="assessments")
    op.drop_table("assessments")
