"""Add password_hash column to faculty table for secure faculty authentication.

Revision ID: 004_faculty_password_hash
Revises: 003_faculty_workload_student_auth
Create Date: 2026-11-23
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "004_faculty_password_hash"
down_revision = "003_faculty_workload_student_auth"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    insp = inspect(bind)

    faculty_cols = [c["name"] for c in insp.get_columns("faculty")]
    if "password_hash" not in faculty_cols:
        op.add_column("faculty", sa.Column("password_hash", sa.String(255), nullable=True))


def downgrade():
    bind = op.get_bind()
    insp = inspect(bind)

    faculty_cols = [c["name"] for c in insp.get_columns("faculty")]
    if "password_hash" in faculty_cols:
        op.drop_column("faculty", "password_hash")
