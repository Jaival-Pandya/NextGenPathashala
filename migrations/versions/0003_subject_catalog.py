"""Add class-scoped subject catalog and backfill subjects from sessions.

Revision ID: 0003_subject_catalog
Revises: 0002_pilot_feedback
Create Date: 2026-10-11
"""
from alembic import op
import sqlalchemy as sa

revision = "0003_subject_catalog"
down_revision = "0002_pilot_feedback"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "subjects",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("institution_id", sa.Integer(), nullable=False),
        sa.Column("class_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["class_id"], ["classes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("class_id", "name", name="uq_subject_name_per_class"),
    )
    op.create_index("ix_subjects_institution_id", "subjects", ["institution_id"])
    op.create_index("ix_subjects_class_id", "subjects", ["class_id"])

    # Seed the catalog from existing scheduled sessions so current subject text
    # is not lost. The session record remains the source of truth for history.
    op.execute(sa.text("""
        INSERT INTO subjects (institution_id, class_id, name, created_by, created_at)
        SELECT institution_id, class_id, subject, MIN(created_by), MIN(created_at)
        FROM class_sessions
        WHERE subject IS NOT NULL AND TRIM(subject) != ''
        GROUP BY institution_id, class_id, subject
    """))


def downgrade():
    # Remove only objects introduced by this migration.
    op.drop_index("ix_subjects_class_id", table_name="subjects")
    op.drop_index("ix_subjects_institution_id", table_name="subjects")
    op.drop_table("subjects")
