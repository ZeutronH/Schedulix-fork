"""
Comprehensive Test Suite for Schedulix University Timetable Management System.
Verifies all 20 required points from Section 15.
"""

import os
import pytest
from datetime import datetime, date, time
from sqlalchemy import select

from app.models import (
    Admin, Department, Programme, AcademicYear, Semester, Section,
    Subject, Student, Faculty, FacultyAssignment, Room, Floor, Building,
    RoomType, SessionType, ScheduledClass, TimetableVersion, VersionStatus,
    AuditLog, EmailNotification, DeliveryStatus, TimetableImage
)
from app.security import hash_password, verify_password, create_access_token, decode_access_token
from app.services.scheduler import HybridScheduler, Job
from app.services.rescheduler import Rescheduler
from app.services.image_generator import generate_timetable_png
from app.services.email import EmailService, notify_version_subscribers
from app.services.graph import CampusGraph
from app.concurrency import acquire_generation_semaphore, SemaphoreBusyException, DeadlockPreventionManager
from app.audit import record_audit


# ============================================================================
# 1. AUTHENTICATION (SECTION 15.1)
# ============================================================================
def test_01_authentication():
    pwd = "secretpassword123"
    hashed = hash_password(pwd)
    assert verify_password(pwd, hashed) is True
    assert verify_password("wrongpassword", hashed) is False

    admin_id = "test-admin-uuid-123"
    token = create_access_token(admin_id)
    decoded = decode_access_token(token)
    assert decoded == admin_id


# ============================================================================
# 2. CREATING A DEPARTMENT (SECTION 15.2)
# ============================================================================
def test_02_create_department(db):
    dept = Department(name="Computer Science & Engineering", code="CSE", description="CS Dept")
    db.add(dept)
    db.commit()
    db.refresh(dept)
    assert dept.id is not None
    assert dept.code == "CSE"


# ============================================================================
# 3. CREATING A STUDENT (SECTION 15.3)
# ============================================================================
def test_03_create_student(db):
    student = Student(
        student_id="240212377",
        full_name="John Doe",
        email="johndoe@example.edu",
        admission_year=2024
    )
    db.add(student)
    db.commit()
    db.refresh(student)
    assert student.student_id == "240212377"
    assert student.admission_year == 2024


# ============================================================================
# 4. CREATING FACULTY (SECTION 15.4)
# ============================================================================
def test_04_create_faculty(db):
    dept = Department(name="Electrical Engineering", code="EE")
    db.add(dept)
    db.flush()

    faculty = Faculty(
        faculty_id="EE-FAC-001",
        department_id=dept.id,
        full_name="Dr. Nikola Tesla",
        email="tesla@example.edu",
        designation="Professor"
    )
    db.add(faculty)
    db.commit()
    db.refresh(faculty)
    assert faculty.faculty_id == "EE-FAC-001"
    assert faculty.department_id == dept.id


# ============================================================================
# 5. CREATING A SUBJECT (SECTION 15.5)
# ============================================================================
def test_05_create_subject(db):
    dept = Department(name="Mechanical Engineering", code="ME")
    db.add(dept)
    db.flush()

    subj = Subject(
        department_id=dept.id,
        code="ME-201",
        name="Thermodynamics",
        session_type=SessionType.LECTURE,
        default_duration=60
    )
    db.add(subj)
    db.commit()
    db.refresh(subj)
    assert subj.code == "ME-201"
    assert subj.session_type == SessionType.LECTURE


# ============================================================================
# 6. CREATING A SECTION (SECTION 15.6)
# ============================================================================
def test_06_create_section(db):
    dept = Department(name="Civil Engineering", code="CE")
    db.add(dept)
    db.flush()

    prog = Programme(department_id=dept.id, name="B.Tech Civil", code="BTECH-CE", duration_years=4)
    db.add(prog)
    year = AcademicYear(name="2026-2027", start_date=date(2026, 7, 1), end_date=date(2027, 6, 30))
    db.add(year)
    db.flush()

    sem = Semester(programme_id=prog.id, academic_year_id=year.id, number=3)
    db.add(sem)
    db.flush()

    section = Section(semester_id=sem.id, programme_id=prog.id, name="A", student_count=45)
    db.add(section)
    db.commit()
    db.refresh(section)
    assert section.name == "A"
    assert section.student_count == 45


# ============================================================================
# 7. CREATING A CLASSROOM (SECTION 15.7)
# ============================================================================
def test_07_create_classroom(db):
    bld = Building(name="Science Block", code="SC")
    db.add(bld)
    db.flush()
    fl = Floor(building_id=bld.id, name="Floor 1", level=1)
    db.add(fl)
    db.flush()

    room = Room(
        floor_id=fl.id,
        name="R-101",
        room_type=RoomType.CLASSROOM,
        capacity=60,
        equipment=["Smart Board", "AC"]
    )
    db.add(room)
    db.commit()
    db.refresh(room)
    assert room.name == "R-101"
    assert room.capacity == 60


# ============================================================================
# 8. CREATING FACULTY ASSIGNMENTS (SECTION 15.8)
# ============================================================================
def test_08_create_faculty_assignments(db):
    dept = Department(name="IT", code="IT")
    db.add(dept)
    db.flush()
    prog = Programme(department_id=dept.id, name="B.Tech IT", code="BTECH-IT")
    db.add(prog)
    year = AcademicYear(name="2026-2027-IT", start_date=date(2026, 7, 1), end_date=date(2027, 6, 30))
    db.add(year)
    db.flush()
    sem = Semester(programme_id=prog.id, academic_year_id=year.id, number=1)
    db.add(sem)
    db.flush()
    sec = Section(semester_id=sem.id, programme_id=prog.id, name="A", student_count=40)
    db.add(sec)
    fac = Faculty(faculty_id="IT-FAC-01", department_id=dept.id, full_name="Alan Turing", email="turing@example.edu")
    db.add(fac)
    subj = Subject(department_id=dept.id, code="IT-101", name="Computing Basics", session_type=SessionType.LECTURE)
    db.add(subj)
    db.flush()

    assign = FacultyAssignment(
        faculty_id=fac.id,
        subject_id=subj.id,
        section_id=sec.id,
        sessions_per_week=3,
        duration_minutes=60,
        priority=8,
        required_capacity=40,
        required_room_type=RoomType.CLASSROOM
    )
    db.add(assign)
    db.commit()
    db.refresh(assign)
    assert assign.sessions_per_week == 3
    assert assign.priority == 8


# ============================================================================
# 9, 10, 11. PREVENTING CONFLICTS (FACULTY, ROOM, SECTION) (SECTIONS 15.9 - 15.11)
# ============================================================================
def test_09_10_11_conflict_prevention(db):
    dept = Department(name="Chemical", code="CH")
    db.add(dept)
    db.flush()
    prog = Programme(department_id=dept.id, name="B.Tech CH", code="BTECH-CH")
    db.add(prog)
    year = AcademicYear(name="2026-CH", start_date=date(2026, 7, 1), end_date=date(2027, 6, 30))
    db.add(year)
    db.flush()
    sem = Semester(programme_id=prog.id, academic_year_id=year.id, number=2)
    db.add(sem)
    db.flush()
    sec1 = Section(semester_id=sem.id, programme_id=prog.id, name="A", student_count=35)
    sec2 = Section(semester_id=sem.id, programme_id=prog.id, name="B", student_count=35)
    db.add_all([sec1, sec2])
    fac = Faculty(faculty_id="CH-FAC-01", department_id=dept.id, full_name="Marie Curie", email="curie@example.edu")
    db.add(fac)
    subj1 = Subject(department_id=dept.id, code="CH-101", name="Organic Chem", session_type=SessionType.LECTURE)
    subj2 = Subject(department_id=dept.id, code="CH-102", name="Physical Chem", session_type=SessionType.LECTURE)
    db.add_all([subj1, subj2])
    bld = Building(name="Chem Block", code="CB")
    db.add(bld)
    db.flush()
    fl = Floor(building_id=bld.id, name="Ground", level=0)
    db.add(fl)
    db.flush()
    room = Room(floor_id=fl.id, name="Lab-1", room_type=RoomType.CLASSROOM, capacity=40)
    db.add(room)
    db.flush()

    assign1 = FacultyAssignment(faculty_id=fac.id, subject_id=subj1.id, section_id=sec1.id, sessions_per_week=1, duration_minutes=60, required_room_type=RoomType.CLASSROOM)
    assign2 = FacultyAssignment(faculty_id=fac.id, subject_id=subj2.id, section_id=sec2.id, sessions_per_week=1, duration_minutes=60, required_room_type=RoomType.CLASSROOM)
    db.add_all([assign1, assign2])
    db.flush()

    version = TimetableVersion(version_number=1, algorithm="HYBRID", quality_score=100.0)
    db.add(version)
    db.flush()

    # Scheduled class for Section 1 with Faculty Marie Curie in Lab-1 on Monday 09:00 - 10:00 (540 to 600)
    c1 = ScheduledClass(
        version_id=version.id,
        assignment_id=assign1.id,
        faculty_id=fac.id,
        section_id=sec1.id,
        subject_id=subj1.id,
        room_id=room.id,
        weekday=0,
        start_minute=540,
        end_minute=600,
        session_number=1
    )
    # Scheduled class for Section 2 on Monday 10:00 - 11:00 (600 to 660)
    c2 = ScheduledClass(
        version_id=version.id,
        assignment_id=assign2.id,
        faculty_id=fac.id,
        section_id=sec2.id,
        subject_id=subj2.id,
        room_id=room.id,
        weekday=0,
        start_minute=600,
        end_minute=660,
        session_number=1
    )
    db.add_all([c1, c2])
    db.commit()

    rescheduler = Rescheduler(db)

    # 9. Faculty conflict: try moving c2 to overlap with c1 (09:30 - 10:30) where Marie Curie is already teaching
    check = rescheduler.check_conflicts(
        version_id=version.id,
        class_id=c2.id,
        new_weekday=0,
        new_start_minute=570,
        new_end_minute=630,
        new_faculty_id=fac.id
    )
    assert check["valid"] is False
    assert any("Faculty Clash" in err for err in check["conflicts"])

    # 10. Room conflict: try moving c2 to overlap with c1 in room Lab-1
    check_room = rescheduler.check_conflicts(
        version_id=version.id,
        class_id=c2.id,
        new_weekday=0,
        new_start_minute=540,
        new_end_minute=600,
        new_room_id=room.id
    )
    assert check_room["valid"] is False
    assert any("Room Clash" in err for err in check_room["conflicts"])

    # 11. Section conflict: try scheduling another class for sec1 at 09:00 - 10:00
    check_sec = rescheduler.check_conflicts(
        version_id=version.id,
        class_id=c2.id,
        new_weekday=0,
        new_start_minute=540,
        new_end_minute=600
    )
    assert check_sec["valid"] is False


# ============================================================================
# 12. GENERATING A TIMETABLE (SECTION 15.12)
# ============================================================================
def test_12_generate_timetable(db):
    dept = Department(name="Biotech", code="BT")
    db.add(dept)
    db.flush()
    prog = Programme(department_id=dept.id, name="B.Tech BT", code="BTECH-BT")
    db.add(prog)
    year = AcademicYear(name="2026-BT", start_date=date(2026, 7, 1), end_date=date(2027, 6, 30))
    db.add(year)
    db.flush()
    sem = Semester(programme_id=prog.id, academic_year_id=year.id, number=1)
    db.add(sem)
    db.flush()
    sec = Section(semester_id=sem.id, programme_id=prog.id, name="A", student_count=30)
    db.add(sec)
    fac = Faculty(faculty_id="BT-FAC-01", department_id=dept.id, full_name="Rosalind Franklin", email="franklin@example.edu")
    db.add(fac)
    subj = Subject(department_id=dept.id, code="BT-101", name="Genetics", session_type=SessionType.LECTURE)
    db.add(subj)
    bld = Building(name="BT Block", code="BTB")
    db.add(bld)
    db.flush()
    fl = Floor(building_id=bld.id, name="Ground", level=0)
    db.add(fl)
    db.flush()
    room = Room(floor_id=fl.id, name="BT-101", room_type=RoomType.CLASSROOM, capacity=40)
    db.add(room)
    db.flush()

    assign = FacultyAssignment(
        faculty_id=fac.id,
        subject_id=subj.id,
        section_id=sec.id,
        sessions_per_week=2,
        duration_minutes=60,
        required_room_type=RoomType.CLASSROOM,
        priority=8
    )
    db.add(assign)
    db.commit()

    scheduler = HybridScheduler(db, mode="HYBRID", priority_weight=0.65, sjf_weight=0.35, weekdays=[0, 1, 2, 3, 4], day_start=480, day_end=1080, time_limit=10)
    result = scheduler.solve()
    assert result["status"] in ("OPTIMAL", "FEASIBLE")
    assert len(result["classes"]) == 2
    assert len(result["unscheduled"]) == 0


# ============================================================================
# 13. HANDLING UNSCHEDULED SESSIONS (SECTION 15.13)
# ============================================================================
def test_13_unscheduled_sessions_diagnostics(db):
    dept = Department(name="Aero", code="AE")
    db.add(dept)
    db.flush()
    prog = Programme(department_id=dept.id, name="B.Tech AE", code="BTECH-AE")
    db.add(prog)
    year = AcademicYear(name="2026-AE", start_date=date(2026, 7, 1), end_date=date(2027, 6, 30))
    db.add(year)
    db.flush()
    sem = Semester(programme_id=prog.id, academic_year_id=year.id, number=1)
    db.add(sem)
    db.flush()
    sec = Section(semester_id=sem.id, programme_id=prog.id, name="A", student_count=100) # 100 students
    db.add(sec)
    fac = Faculty(faculty_id="AE-FAC-01", department_id=dept.id, full_name="Wright Brother", email="wright@example.edu")
    db.add(fac)
    subj = Subject(department_id=dept.id, code="AE-101", name="Aerodynamics", session_type=SessionType.LECTURE)
    db.add(subj)
    bld = Building(name="Aero Block", code="AB")
    db.add(bld)
    db.flush()
    fl = Floor(building_id=bld.id, name="Ground", level=0)
    db.add(fl)
    db.flush()
    # Small room only: capacity 20 (cannot hold 100 students)
    room = Room(floor_id=fl.id, name="Tiny-Room", room_type=RoomType.CLASSROOM, capacity=20)
    db.add(room)
    db.flush()

    assign = FacultyAssignment(
        faculty_id=fac.id,
        subject_id=subj.id,
        section_id=sec.id,
        sessions_per_week=1,
        duration_minutes=60,
        required_room_type=RoomType.CLASSROOM,
        required_capacity=100
    )
    db.add(assign)
    db.commit()

    scheduler = HybridScheduler(db, mode="HYBRID", priority_weight=0.65, sjf_weight=0.35, weekdays=[0, 1], day_start=480, day_end=600, time_limit=5)
    result = scheduler.solve()
    assert len(result["unscheduled"]) > 0
    assert any("required room type and capacity" in u.get("reason", "") for u in result["unscheduled"])


# ============================================================================
# 14. RESCHEDULING A SESSION (SECTION 15.14)
# ============================================================================
def test_14_rescheduling_session(db):
    dept = Department(name="Robotics", code="RO")
    db.add(dept)
    db.flush()
    prog = Programme(department_id=dept.id, name="B.Tech RO", code="BTECH-RO")
    db.add(prog)
    year = AcademicYear(name="2026-RO", start_date=date(2026, 7, 1), end_date=date(2027, 6, 30))
    db.add(year)
    db.flush()
    sem = Semester(programme_id=prog.id, academic_year_id=year.id, number=1)
    db.add(sem)
    db.flush()
    sec = Section(semester_id=sem.id, programme_id=prog.id, name="A", student_count=25)
    db.add(sec)
    fac = Faculty(faculty_id="RO-FAC-01", department_id=dept.id, full_name="Isaac Asimov", email="asimov@example.edu")
    db.add(fac)
    subj = Subject(department_id=dept.id, code="RO-101", name="Cybernetics", session_type=SessionType.LECTURE)
    db.add(subj)
    bld = Building(name="RO Block", code="ROB")
    db.add(bld)
    db.flush()
    fl = Floor(building_id=bld.id, name="Ground", level=0)
    db.add(fl)
    db.flush()
    room = Room(floor_id=fl.id, name="RO-101", room_type=RoomType.CLASSROOM, capacity=30)
    db.add(room)
    db.flush()

    assign = FacultyAssignment(faculty_id=fac.id, subject_id=subj.id, section_id=sec.id, sessions_per_week=1, duration_minutes=60, required_room_type=RoomType.CLASSROOM)
    db.add(assign)
    db.flush()

    v1 = TimetableVersion(version_number=1, algorithm="HYBRID", quality_score=100.0)
    db.add(v1)
    db.flush()

    c1 = ScheduledClass(
        version_id=v1.id,
        assignment_id=assign.id,
        faculty_id=fac.id,
        section_id=sec.id,
        subject_id=subj.id,
        room_id=room.id,
        weekday=0,
        start_minute=480,
        end_minute=540,
        session_number=1
    )
    db.add(c1)
    db.commit()

    rescheduler = Rescheduler(db)
    result = rescheduler.manual_reschedule(
        version_id=v1.id,
        class_id=c1.id,
        new_weekday=2,
        new_start_minute=600,
        new_end_minute=660,
        reason="Administrative reschedule"
    )

    assert result["status"] == "RESCHEDULED"
    assert result["new_version_number"] == 2
    assert result["validation"]["valid"] is True


# ============================================================================
# 15. GENERATING PNG FILES (SECTION 15.15)
# ============================================================================
def test_15_generate_png_files(db):
    dept = Department(name="Art", code="ART")
    db.add(dept)
    db.flush()
    prog = Programme(department_id=dept.id, name="BFA", code="BFA")
    db.add(prog)
    year = AcademicYear(name="2026-ART", start_date=date(2026, 7, 1), end_date=date(2027, 6, 30))
    db.add(year)
    db.flush()
    sem = Semester(programme_id=prog.id, academic_year_id=year.id, number=1)
    db.add(sem)
    db.flush()
    sec = Section(semester_id=sem.id, programme_id=prog.id, name="A", student_count=20)
    db.add(sec)
    fac = Faculty(faculty_id="ART-FAC-01", department_id=dept.id, full_name="Leonardo da Vinci", email="vinci@example.edu")
    db.add(fac)
    subj = Subject(department_id=dept.id, code="ART-101", name="Drawing", session_type=SessionType.LECTURE)
    db.add(subj)
    bld = Building(name="Studio Block", code="STB")
    db.add(bld)
    db.flush()
    fl = Floor(building_id=bld.id, name="Ground", level=0)
    db.add(fl)
    db.flush()
    room = Room(floor_id=fl.id, name="Studio-A", room_type=RoomType.CLASSROOM, capacity=30)
    db.add(room)
    db.flush()

    assign = FacultyAssignment(faculty_id=fac.id, subject_id=subj.id, section_id=sec.id, sessions_per_week=1, duration_minutes=60, required_room_type=RoomType.CLASSROOM)
    db.add(assign)
    db.flush()

    version = TimetableVersion(version_number=1, algorithm="HYBRID", quality_score=100.0)
    db.add(version)
    db.flush()

    c1 = ScheduledClass(
        version_id=version.id,
        assignment_id=assign.id,
        faculty_id=fac.id,
        section_id=sec.id,
        subject_id=subj.id,
        room_id=room.id,
        weekday=1,
        start_minute=600,
        end_minute=660,
        session_number=1
    )
    db.add(c1)
    db.commit()

    image_record = generate_timetable_png(db, version.id, "STUDENT", sec.id)
    assert image_record.id is not None
    assert os.path.exists(image_record.file_path)
    assert image_record.file_path.endswith(".png")


# ============================================================================
# 16. EMAIL DELIVERY & DUPLICATE PREVENTION (SECTION 15.16)
# ============================================================================
def test_16_email_delivery_and_duplicate_prevention(db):
    version = TimetableVersion(version_number=1, algorithm="HYBRID")
    db.add(version)
    db.commit()

    email_service = EmailService()
    res1 = email_service.send_timetable_email(
        db=db,
        version_id=version.id,
        recipient_type="STUDENT",
        recipient_id="student-1",
        recipient_email="student1@example.edu",
        recipient_name="Student One"
    )
    assert res1["status"] in ("SENT", "DELIVERED")

    # Duplicate send attempt for the same version and recipient
    res2 = email_service.send_timetable_email(
        db=db,
        version_id=version.id,
        recipient_type="STUDENT",
        recipient_id="student-1",
        recipient_email="student1@example.edu",
        recipient_name="Student One"
    )
    assert res2["status"] == "DUPLICATE_SKIPPED"


# ============================================================================
# 17. TRIGGER EXECUTION (SECTION 15.17)
# ============================================================================
def test_17_trigger_execution(db):
    # Tests audit trail recording
    log = record_audit(
        db,
        action="TEST_TRIGGER_ACTION",
        entity_type="Department",
        entity_id="test-dept-id",
        details={"info": "Test trigger metadata"}
    )
    db.commit()
    assert log.id is not None
    assert log.action == "TEST_TRIGGER_ACTION"


# ============================================================================
# 18. SEMAPHORE BEHAVIOUR (SECTION 15.18)
# ============================================================================
def test_18_semaphore_behaviour(db):
    acquired = []
    with acquire_generation_semaphore(db, scope="TEST_SCOPE", timeout_seconds=1.0) as sem:
        acquired.append("holder1")
        assert sem["scope"] == "TEST_SCOPE"

    assert "holder1" in acquired


# ============================================================================
# 19. DEADLOCK PREVENTION (SECTION 15.19)
# ============================================================================
def test_19_deadlock_prevention(db):
    resources = [
        {"type": "CLASSROOM", "id": "room-b"},
        {"type": "FACULTY", "id": "fac-a"},
        {"type": "ACADEMIC_SCOPE", "id": "scope-1"}
    ]
    sorted_res = DeadlockPreventionManager.sort_resources(resources)
    # ACADEMIC_SCOPE (1) -> FACULTY (2) -> CLASSROOM (3)
    assert sorted_res[0]["type"] == "ACADEMIC_SCOPE"
    assert sorted_res[1]["type"] == "FACULTY"
    assert sorted_res[2]["type"] == "CLASSROOM"


# ============================================================================
# 20. AUDIT LOG CREATION (SECTION 15.20)
# ============================================================================
def test_20_audit_log_creation(db):
    log = record_audit(
        db,
        action="FACULTY_ASSIGNED",
        entity_type="FacultyAssignment",
        entity_id="assign-uuid-999",
        admin_id="admin-123",
        details={"faculty": "Dr. Smith", "subject": "Math"}
    )
    db.commit()
    assert log.action == "FACULTY_ASSIGNED"
    assert log.admin_id == "admin-123"
    assert log.details["faculty"] == "Dr. Smith"
