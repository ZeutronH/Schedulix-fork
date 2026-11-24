"""Add academic hierarchy enhancements to subjects, students and timetable_versions."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text

revision = "002_academic_hierarchy"
down_revision = "001_initial"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    insp = inspect(bind)

    # 1. Update subjects
    subject_cols = [c["name"] for c in insp.get_columns("subjects")]
    if "programme_id" not in subject_cols:
        op.add_column("subjects", sa.Column("programme_id", sa.String(36), sa.ForeignKey("programmes.id"), nullable=True))
    if "semester_number" not in subject_cols:
        op.add_column("subjects", sa.Column("semester_number", sa.Integer(), nullable=True))
    if "semester_id" not in subject_cols:
        op.add_column("subjects", sa.Column("semester_id", sa.String(36), sa.ForeignKey("semesters.id"), nullable=True))

    # 2. Update students
    student_cols = [c["name"] for c in insp.get_columns("students")]
    if "department_id" not in student_cols:
        op.add_column("students", sa.Column("department_id", sa.String(36), sa.ForeignKey("departments.id"), nullable=True))
    if "programme_id" not in student_cols:
        op.add_column("students", sa.Column("programme_id", sa.String(36), sa.ForeignKey("programmes.id"), nullable=True))
    if "current_year" not in student_cols:
        op.add_column("students", sa.Column("current_year", sa.Integer(), nullable=True))
    if "current_semester" not in student_cols:
        op.add_column("students", sa.Column("current_semester", sa.Integer(), nullable=True))

    # 3. Update timetable_versions
    tv_cols = [c["name"] for c in insp.get_columns("timetable_versions")]
    if "programme_id" not in tv_cols:
        op.add_column("timetable_versions", sa.Column("programme_id", sa.String(36), sa.ForeignKey("programmes.id"), nullable=True))
    if "academic_year_id" not in tv_cols:
        op.add_column("timetable_versions", sa.Column("academic_year_id", sa.String(36), sa.ForeignKey("academic_years.id"), nullable=True))
    if "semester_id" not in tv_cols:
        op.add_column("timetable_versions", sa.Column("semester_id", sa.String(36), sa.ForeignKey("semesters.id"), nullable=True))
    if "section_id" not in tv_cols:
        op.add_column("timetable_versions", sa.Column("section_id", sa.String(36), sa.ForeignKey("sections.id"), nullable=True))

    # 4. Backfill existing subjects
    # Link subjects to the programme in the same department and semester 3 if semester_number is null
    bind.execute(text("""
        UPDATE subjects s
        SET programme_id = p.id,
            semester_number = 3
        FROM programmes p
        WHERE s.department_id = p.department_id
          AND s.programme_id IS NULL;
    """))

    # Link semester_id on subjects matching programme_id and semester_number
    bind.execute(text("""
        UPDATE subjects sub
        SET semester_id = sem.id
        FROM semesters sem
        WHERE sub.programme_id = sem.programme_id
          AND sub.semester_number = sem.number
          AND sub.semester_id IS NULL;
    """))

    # 5. Backfill existing students from their active enrolments
    bind.execute(text("""
        UPDATE students stu
        SET department_id = prog.department_id,
            programme_id = prog.id,
            current_semester = sem.number,
            current_year = (sem.number + 1) / 2
        FROM enrolments enr
        JOIN sections sec ON enr.section_id = sec.id
        JOIN semesters sem ON sec.semester_id = sem.id
        JOIN programmes prog ON sec.programme_id = prog.id
        WHERE enr.student_id = stu.id
          AND enr.active = true
          AND stu.programme_id IS NULL;
    """))


def downgrade():
    bind = op.get_bind()
    insp = inspect(bind)

    tv_cols = [c["name"] for c in insp.get_columns("timetable_versions")]
    for col in ["section_id", "semester_id", "academic_year_id", "programme_id"]:
        if col in tv_cols:
            op.drop_column("timetable_versions", col)

    student_cols = [c["name"] for c in insp.get_columns("students")]
    for col in ["current_semester", "current_year", "programme_id", "department_id"]:
        if col in student_cols:
            op.drop_column("students", col)

    subject_cols = [c["name"] for c in insp.get_columns("subjects")]
    for col in ["semester_id", "semester_number", "programme_id"]:
        if col in subject_cols:
            op.drop_column("subjects", col)
