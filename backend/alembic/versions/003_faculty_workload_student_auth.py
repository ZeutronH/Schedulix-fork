"""Add faculty workload protection, qualifications, eligibility and student authentication.

Revision ID: 003_faculty_workload_student_auth
Revises: 002_academic_hierarchy
Create Date: 2026-11-23
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from datetime import datetime

revision = "003_faculty_workload_student_auth"
down_revision = "002_academic_hierarchy"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    insp = inspect(bind)

    # 1. Update faculty table
    faculty_cols = [c["name"] for c in insp.get_columns("faculty")]
    if "highest_qualification" not in faculty_cols:
        op.add_column("faculty", sa.Column("highest_qualification", sa.String(100), nullable=True))
    if "specialisation" not in faculty_cols:
        op.add_column("faculty", sa.Column("specialisation", sa.String(150), nullable=True))
    if "max_classes_per_day" not in faculty_cols:
        op.add_column("faculty", sa.Column("max_classes_per_day", sa.Integer(), nullable=False, server_default="4"))
    if "max_classes_per_week" not in faculty_cols:
        op.add_column("faculty", sa.Column("max_classes_per_week", sa.Integer(), nullable=False, server_default="18"))
    if "max_consecutive_hours" not in faculty_cols:
        op.add_column("faculty", sa.Column("max_consecutive_hours", sa.Integer(), nullable=False, server_default="2"))
    if "min_break_minutes" not in faculty_cols:
        op.add_column("faculty", sa.Column("min_break_minutes", sa.Integer(), nullable=False, server_default="15"))
    if "cross_department_approved" not in faculty_cols:
        op.add_column("faculty", sa.Column("cross_department_approved", sa.Boolean(), nullable=False, server_default="false"))

    # 2. Update students table
    student_cols = [c["name"] for c in insp.get_columns("students")]
    if "password_hash" not in student_cols:
        op.add_column("students", sa.Column("password_hash", sa.String(255), nullable=True))

    # 3. Create faculty_subject_eligibilities table
    tables = insp.get_table_names()
    if "faculty_subject_eligibilities" not in tables:
        op.create_table(
            "faculty_subject_eligibilities",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("faculty_id", sa.String(36), sa.ForeignKey("faculty.id", ondelete="CASCADE"), nullable=False),
            sa.Column("subject_id", sa.String(36), sa.ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False, default=datetime.utcnow),
            sa.UniqueConstraint("faculty_id", "subject_id", name="uq_faculty_subject_eligibility")
        )

    # 4. Create faculty_semester_eligibilities table
    if "faculty_semester_eligibilities" not in tables:
        op.create_table(
            "faculty_semester_eligibilities",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("faculty_id", sa.String(36), sa.ForeignKey("faculty.id", ondelete="CASCADE"), nullable=False),
            sa.Column("semester_number", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False, default=datetime.utcnow),
            sa.UniqueConstraint("faculty_id", "semester_number", name="uq_faculty_semester_eligibility"),
            sa.CheckConstraint("semester_number BETWEEN 1 AND 12", name="ck_faculty_semester_eligibility_number")
        )


def downgrade():
    op.drop_table("faculty_semester_eligibilities")
    op.drop_table("faculty_subject_eligibilities")
    op.drop_column("students", "password_hash")
    op.drop_column("faculty", "cross_department_approved")
    op.drop_column("faculty", "min_break_minutes")
    op.drop_column("faculty", "max_consecutive_hours")
    op.drop_column("faculty", "max_classes_per_week")
    op.drop_column("faculty", "max_classes_per_day")
    op.drop_column("faculty", "specialisation")
    op.drop_column("faculty", "highest_qualification")
