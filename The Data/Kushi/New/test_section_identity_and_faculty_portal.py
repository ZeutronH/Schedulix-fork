"""
Unit and Integration Tests for Section Academic Identity and Faculty Timetable Portal.
Tests:
1. Section identity generation and display throughout API endpoints.
2. Faculty authentication, initial login, and admin password reset.
3. Strict RBAC enforcement (ADMIN, FACULTY, STUDENT mutual isolation).
4. Faculty portal profile, workload metrics, and announcements.
5. Consolidated faculty timetable combining multiple sections.
6. Authenticated faculty timetable PNG generation and download.
7. Scheduler multi-section double-booking prevention.
"""

import pytest
from datetime import date, datetime
from fastapi.testclient import TestClient

from app.main import app
from app.models import (
    Admin, Department, Programme, AcademicYear, Semester, Section,
    Subject, Student, Faculty, FacultyAssignment, Room, Floor, Building,
    RoomType, SessionType, ScheduledClass, TimetableVersion, VersionStatus,
    Enrolment, FacultySubjectEligibility, FacultySemesterEligibility, AuditLog
)
from app.security import hash_password, create_access_token


@pytest.fixture
def test_client(db):
    from app.database import get_db
    app.dependency_overrides[get_db] = lambda: db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers(db):
    from app.dependencies import get_current_admin
    admin = Admin(
        username="fac_portal_admin",
        email="fac_admin@example.edu",
        password_hash=hash_password("SuperSecretAdmin123!")
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    app.dependency_overrides[get_current_admin] = lambda: admin
    token = create_access_token(admin.id, role="ADMIN")
    return {"Authorization": f"Bearer {token}"}


# ============================================================================
# 1. SECTION ACADEMIC IDENTITY THROUGHOUT APPLICATION
# ============================================================================
def test_section_identity_throughout_api(db, test_client, auth_headers):
    # Create Department
    dept = Department(name="Mechanical Engineering", code="ME", description="Mech Dept")
    db.add(dept)
    db.commit()
    db.refresh(dept)

    # Create Programme
    prog = Programme(name="B.Tech Mechanical", code="BTECH-ME", duration_years=4, department_id=dept.id)
    db.add(prog)
    db.commit()
    db.refresh(prog)

    # Create Academic Year & Semester
    ay = AcademicYear(name="2026-2027", start_date=date(2026, 8, 1), end_date=date(2027, 5, 31), active=True)
    db.add(ay)
    db.commit()
    db.refresh(ay)

    sem = Semester(programme_id=prog.id, academic_year_id=ay.id, number=3)
    db.add(sem)
    db.commit()
    db.refresh(sem)

    # Create Section A
    sec = Section(name="A", student_count=60, semester_id=sem.id, programme_id=prog.id)
    db.add(sec)
    db.commit()
    db.refresh(sec)

    # 1.1 Verify Section Identity in /api/academic/sections
    res = test_client.get("/api/academic/sections", headers=auth_headers)
    assert res.status_code == 200
    sec_data = next((s for s in res.json() if s["id"] == sec.id), None)
    assert sec_data is not None
    assert sec_data["section_code"] == "BTECH-ME-SEM3-A"
    assert "B.Tech Mechanical" in sec_data["display_name"]
    assert "Semester 3" in sec_data["display_name"]
    assert "Section A" in sec_data["display_name"]

    # 1.2 Create Faculty and Subject, then Assignment
    fac = Faculty(
        faculty_id="FAC_ME_01",
        full_name="Dr. Alan Turing",
        email="alan.turing@example.edu",
        department_id=dept.id,
        password_hash=hash_password("schedulix2026")
    )
    subj = Subject(
        code="ME301",
        name="Thermodynamics",
        session_type=SessionType.LECTURE,
        default_duration=60,
        department_id=dept.id,
        programme_id=prog.id,
        semester_id=sem.id
    )
    db.add_all([fac, subj])
    db.commit()
    db.refresh(fac)
    db.refresh(subj)

    asgn = FacultyAssignment(
        faculty_id=fac.id,
        subject_id=subj.id,
        section_id=sec.id,
        sessions_per_week=3,
        duration_minutes=60,
        required_room_type=RoomType.CLASSROOM,
        active=True
    )
    db.add(asgn)
    db.commit()

    # Verify section identity in assignments
    asgn_res = test_client.get("/api/academic/assignments", headers=auth_headers)
    assert asgn_res.status_code == 200
    asgn_item = next((a for a in asgn_res.json() if a["id"] == asgn.id), None)
    assert asgn_item is not None
    assert asgn_item["section_code"] == "BTECH-ME-SEM3-A"
    assert "B.Tech Mechanical" in asgn_item["section_display_name"]

    # 1.3 Create Student Enrolment
    stu = Student(
        student_id="STU_ME_01",
        full_name="John Doe",
        email="john.doe@example.edu",
        admission_year=2024
    )
    db.add(stu)
    db.commit()
    db.refresh(stu)

    enr = Enrolment(
        student_id=stu.id,
        section_id=sec.id,
        active=True
    )
    db.add(enr)
    db.commit()

    # Verify section identity in students endpoint
    stu_res = test_client.get("/api/academic/students", headers=auth_headers)
    assert stu_res.status_code == 200
    stu_item = next((s for s in stu_res.json() if s["id"] == stu.id), None)
    assert stu_item is not None
    assert stu_item["section_code"] == "BTECH-ME-SEM3-A"
    assert "B.Tech Mechanical" in stu_item["section_display_name"]

    # 1.4 Verify section identity in Faculty Workload Overview
    wl_res = test_client.get("/api/academic/faculty-workload/overview", headers=auth_headers)
    assert wl_res.status_code == 200
    fac_wl = next((f for f in wl_res.json()["faculty_workload"] if f["id"] == fac.id), None)
    assert fac_wl is not None
    assert len(fac_wl["assignments"]) > 0
    assert fac_wl["assignments"][0]["section_code"] == "BTECH-ME-SEM3-A"


# ============================================================================
# 2. FACULTY AUTHENTICATION AND ADMIN PASSWORD RESET
# ============================================================================
def test_faculty_authentication_and_password_reset(db, test_client, auth_headers):
    dept = Department(name="Computer Science", code="CS", description="CS")
    db.add(dept)
    db.commit()
    db.refresh(dept)

    # Create faculty with initial password
    initial_pass = "InitialFacultyPassword2026!"
    fac = Faculty(
        faculty_id="FAC_AUTH_01",
        full_name="Dr. Ada Lovelace",
        email="ada.lovelace@example.edu",
        department_id=dept.id,
        password_hash=hash_password(initial_pass)
    )
    db.add(fac)
    db.commit()
    db.refresh(fac)

    # 2.1 Login with wrong password -> 401
    bad_login = test_client.post("/api/auth/faculty-login", json={
        "identifier": "FAC_AUTH_01",
        "password": "WrongPassword123"
    })
    assert bad_login.status_code == 401

    # 2.2 Login with initial valid password -> 200
    good_login = test_client.post("/api/auth/faculty-login", json={
        "identifier": "ada.lovelace@example.edu",
        "password": initial_pass
    })
    assert good_login.status_code == 200
    token_data = good_login.json()
    assert token_data["role"] == "FACULTY"
    fac_token = token_data["access_token"]
    fac_headers = {"Authorization": f"Bearer {fac_token}"}

    # Verify faculty-me endpoint
    me_res = test_client.get("/api/auth/faculty-me", headers=fac_headers)
    assert me_res.status_code == 200
    assert me_res.json()["faculty_id"] == "FAC_AUTH_01"

    # 2.3 Admin resets faculty password
    new_password = "NewlyResetPasswordByAdmin999!"
    reset_res = test_client.post(
        f"/api/academic/faculty/{fac.id}/reset-password",
        json={"new_password": new_password},
        headers=auth_headers
    )
    assert reset_res.status_code == 200
    assert "successfully" in reset_res.json()["message"]

    # 2.4 Old password no longer works
    old_login = test_client.post("/api/auth/faculty-login", json={
        "identifier": "FAC_AUTH_01",
        "password": initial_pass
    })
    assert old_login.status_code == 401

    # 2.5 New password works
    new_login = test_client.post("/api/auth/faculty-login", json={
        "identifier": "FAC_AUTH_01",
        "password": new_password
    })
    assert new_login.status_code == 200
    assert new_login.json()["role"] == "FACULTY"


# ============================================================================
# 3. STRICT ROLE-BASED ACCESS CONTROL (RBAC)
# ============================================================================
def test_strict_role_based_access_control(db, test_client):
    # Setup Real Admin
    admin = Admin(
        username="rbac_admin_tester",
        email="rbac_admin_tester@example.edu",
        password_hash=hash_password("adminSecret123!")
    )
    db.add(admin)
    db.commit()
    admin_token = create_access_token(admin.id, role="ADMIN")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # Setup Faculty
    dept = Department(name="Electrical Engineering", code="EE", description="EE")
    db.add(dept)
    db.commit()
    db.refresh(dept)

    fac = Faculty(
        faculty_id="FAC_RBAC_01",
        full_name="Prof. Nikola Tesla",
        email="nikola.tesla@example.edu",
        department_id=dept.id,
        password_hash=hash_password("tesla2026")
    )
    stu = Student(
        student_id="STU_RBAC_01",
        full_name="Jane Student",
        email="jane.student@example.edu",
        admission_year=2024,
        password_hash=hash_password("student2026")
    )
    db.add_all([fac, stu])
    db.commit()
    db.refresh(fac)
    db.refresh(stu)

    # Login Faculty
    fac_res = test_client.post("/api/auth/faculty-login", json={
        "identifier": "FAC_RBAC_01",
        "password": "tesla2026"
    })
    assert fac_res.status_code == 200
    fac_headers = {"Authorization": f"Bearer {fac_res.json()['access_token']}"}

    # Login Student
    stu_res = test_client.post("/api/auth/student-login", json={
        "identifier": "STU_RBAC_01",
        "password": "student2026"
    })
    assert stu_res.status_code == 200
    stu_headers = {"Authorization": f"Bearer {stu_res.json()['access_token']}"}

    # Admin CAN access Admin routes
    admin_to_admin = test_client.post("/api/academic/departments", json={
        "name": "Allowed Dept",
        "code": "ALLOW"
    }, headers=admin_headers)
    assert admin_to_admin.status_code == 200

    # 3.1 Faculty forbidden from Admin routes
    fac_to_admin = test_client.post("/api/academic/departments", json={
        "name": "Hacked Dept",
        "code": "HACK"
    }, headers=fac_headers)
    assert fac_to_admin.status_code == 403

    fac_to_sched = test_client.post("/api/scheduling/generate", json={
        "mode": "HYBRID"
    }, headers=fac_headers)
    assert fac_to_sched.status_code == 403

    # 3.2 Faculty forbidden from Student routes
    fac_to_student = test_client.get("/api/student/profile", headers=fac_headers)
    assert fac_to_student.status_code == 403

    # 3.3 Student forbidden from Faculty routes
    stu_to_faculty = test_client.get("/api/faculty/profile", headers=stu_headers)
    assert stu_to_faculty.status_code == 403

    stu_to_fac_tt = test_client.get("/api/faculty/timetable", headers=stu_headers)
    assert stu_to_fac_tt.status_code == 403

    # 3.4 Student forbidden from Admin routes
    stu_to_admin = test_client.get("/api/academic/departments", headers=stu_headers)
    assert stu_to_admin.status_code == 403


# ============================================================================
# 4. FACULTY PORTAL PROFILE AND ANNOUNCEMENTS
# ============================================================================
def test_faculty_portal_profile_and_announcements(db, test_client):
    dept = Department(name="Civil Engineering", code="CE", description="CE Dept")
    db.add(dept)
    db.commit()
    db.refresh(dept)

    fac = Faculty(
        faculty_id="FAC_CE_01",
        full_name="Dr. Isambard Brunel",
        email="brunel@example.edu",
        department_id=dept.id,
        designation="Professor",
        highest_qualification="Ph.D. in Structural Engineering",
        specialisation="Bridge Construction & Statics",
        max_classes_per_day=3,
        max_classes_per_week=12,
        max_consecutive_hours=2,
        min_break_minutes=15,
        password_hash=hash_password("brunel2026")
    )
    db.add(fac)
    db.commit()
    db.refresh(fac)

    # Add eligibility
    sem_elig = FacultySemesterEligibility(faculty_id=fac.id, semester_number=5)
    db.add(sem_elig)
    db.commit()

    # Login
    login_res = test_client.post("/api/auth/faculty-login", json={
        "identifier": "FAC_CE_01",
        "password": "brunel2026"
    })
    headers = {"Authorization": f"Bearer {login_res.json()['access_token']}"}

    # 4.1 Check Profile
    prof_res = test_client.get("/api/faculty/profile", headers=headers)
    assert prof_res.status_code == 200
    pdata = prof_res.json()
    assert pdata["faculty"]["full_name"] == "Dr. Isambard Brunel"
    assert pdata["faculty"]["highest_qualification"] == "Ph.D. in Structural Engineering"
    assert pdata["department"]["code"] == "CE"
    assert pdata["workload_limits"]["max_classes_per_day"] == 3
    assert pdata["workload_limits"]["max_classes_per_week"] == 12
    assert 5 in pdata["eligible_semesters"]

    # 4.2 Check Announcements
    log = AuditLog(
        action="PUBLISH",
        entity_type="TIMETABLE",
        details={"note": "Civil Engineering Fall Timetable Published", "version_number": 1}
    )
    db.add(log)
    db.commit()

    ann_res = test_client.get("/api/faculty/announcements", headers=headers)
    assert ann_res.status_code == 200
    assert len(ann_res.json()) > 0
    assert "Published" in ann_res.json()[0]["title"]


# ============================================================================
# 5. CONSOLIDATED FACULTY TIMETABLE & AUTHENTICATED PNG DOWNLOAD
# ============================================================================
def test_faculty_consolidated_timetable_and_png_download(db, test_client):
    # Setup Hierarchy
    dept = Department(name="Computer Science", code="CS", description="CS")
    db.add(dept)
    db.commit()
    db.refresh(dept)

    prog = Programme(name="B.Tech Computer Science", code="BTECH-CS", duration_years=4, department_id=dept.id)
    db.add(prog)
    db.commit()
    db.refresh(prog)

    ay = AcademicYear(name="2026-2027", start_date=date(2026, 8, 1), end_date=date(2027, 5, 31), active=True)
    db.add(ay)
    db.commit()
    db.refresh(ay)

    sem = Semester(programme_id=prog.id, academic_year_id=ay.id, number=1)
    db.add(sem)
    db.commit()
    db.refresh(sem)

    sec_a = Section(name="A", student_count=50, semester_id=sem.id, programme_id=prog.id)
    sec_b = Section(name="B", student_count=50, semester_id=sem.id, programme_id=prog.id)
    db.add_all([sec_a, sec_b])
    db.commit()
    db.refresh(sec_a)
    db.refresh(sec_b)

    fac = Faculty(
        faculty_id="FAC_MULTI_01",
        full_name="Prof. Grace Hopper",
        email="hopper@example.edu",
        department_id=dept.id,
        max_classes_per_week=18,
        password_hash=hash_password("hopper2026")
    )
    subj1 = Subject(
        code="CS101",
        name="Intro to Programming",
        session_type=SessionType.LECTURE,
        default_duration=60,
        department_id=dept.id,
        programme_id=prog.id,
        semester_id=sem.id
    )
    subj2 = Subject(
        code="CS102",
        name="Discrete Mathematics",
        session_type=SessionType.LECTURE,
        default_duration=60,
        department_id=dept.id,
        programme_id=prog.id,
        semester_id=sem.id
    )
    bld = Building(name="Turing Hall", code="TH", available=True)
    db.add_all([fac, subj1, subj2, bld])
    db.commit()
    db.refresh(bld)

    flr = Floor(name="Floor 1", level=1, building_id=bld.id)
    db.add(flr)
    db.commit()
    db.refresh(flr)

    room1 = Room(name="Room 101", room_type=RoomType.CLASSROOM, capacity=60, floor_id=flr.id, available=True)
    room2 = Room(name="Room 102", room_type=RoomType.CLASSROOM, capacity=60, floor_id=flr.id, available=True)
    db.add_all([room1, room2])
    db.commit()
    db.refresh(room1)
    db.refresh(room2)

    # Create published timetable version
    v = TimetableVersion(
        version_number=1,
        status=VersionStatus.PUBLISHED,
        algorithm="HYBRID",
        academic_year_id=ay.id,
        published_at=datetime.utcnow()
    )
    db.add(v)
    db.commit()
    db.refresh(v)

    # Create assignments
    asgn1 = FacultyAssignment(
        faculty_id=fac.id,
        subject_id=subj1.id,
        section_id=sec_a.id,
        sessions_per_week=3,
        duration_minutes=60,
        required_room_type=RoomType.CLASSROOM,
        active=True
    )
    asgn2 = FacultyAssignment(
        faculty_id=fac.id,
        subject_id=subj2.id,
        section_id=sec_b.id,
        sessions_per_week=3,
        duration_minutes=60,
        required_room_type=RoomType.CLASSROOM,
        active=True
    )
    db.add_all([asgn1, asgn2])
    db.commit()
    db.refresh(asgn1)
    db.refresh(asgn2)

    # Class 1: Monday 09:00 - 10:00 for Section A
    c1 = ScheduledClass(
        version_id=v.id,
        assignment_id=asgn1.id,
        subject_id=subj1.id,
        faculty_id=fac.id,
        section_id=sec_a.id,
        room_id=room1.id,
        weekday=0,  # Monday
        start_minute=540,
        end_minute=600,
        session_number=1
    )
    # Class 2: Tuesday 10:00 - 11:00 for Section B
    c2 = ScheduledClass(
        version_id=v.id,
        assignment_id=asgn2.id,
        subject_id=subj2.id,
        faculty_id=fac.id,
        section_id=sec_b.id,
        room_id=room2.id,
        weekday=1,  # Tuesday
        start_minute=600,
        end_minute=660,
        session_number=1
    )
    db.add_all([c1, c2])
    db.commit()

    # Login Faculty
    login_res = test_client.post("/api/auth/faculty-login", json={
        "identifier": "FAC_MULTI_01",
        "password": "hopper2026"
    })
    headers = {"Authorization": f"Bearer {login_res.json()['access_token']}"}

    # 5.1 Fetch Consolidated Timetable
    tt_res = test_client.get("/api/faculty/timetable", headers=headers)
    assert tt_res.status_code == 200
    data = tt_res.json()
    assert data["status"] == "PUBLISHED"
    assert len(data["classes"]) == 2

    # Check that both Section A and Section B are present
    sec_codes = {c["section_code"] for c in data["classes"]}
    assert "BTECH-CS-SEM1-A" in sec_codes
    assert "BTECH-CS-SEM1-B" in sec_codes

    # Check summary metrics
    summary = data["summary"]
    assert summary["total_classes"] == 2
    assert summary["distinct_sections"] == 2
    assert summary["distinct_subjects"] == 2
    assert len(summary["conflicts"]) == 0

    # 5.2 Test Authenticated PNG Download
    png_res = test_client.get("/api/faculty/timetable/download", headers=headers)
    assert png_res.status_code == 200
    assert png_res.headers["content-type"] == "image/png"
    assert "attachment" in png_res.headers["content-disposition"]
    assert "filename=" in png_res.headers["content-disposition"]
    # Verify binary PNG magic header
    content = png_res.content
    assert len(content) > 100
    assert content[:8] == b"\x89PNG\r\n\x1a\n"


# ============================================================================
# 6. SCHEDULER MULTI-SECTION DOUBLE BOOKING PREVENTION
# ============================================================================
def test_scheduler_prevents_faculty_multi_section_double_booking(db):
    from app.services.scheduler import HybridScheduler

    dept = Department(name="Physics", code="PHY", description="Physics Dept")
    db.add(dept)
    db.commit()
    db.refresh(dept)

    prog = Programme(name="B.Tech Physics", code="BTECH-PHY", duration_years=4, department_id=dept.id)
    db.add(prog)
    db.commit()
    db.refresh(prog)

    ay = AcademicYear(name="2026-2027", start_date=date(2026, 8, 1), end_date=date(2027, 5, 31), active=True)
    db.add(ay)
    db.commit()
    db.refresh(ay)

    sem = Semester(programme_id=prog.id, academic_year_id=ay.id, number=1)
    db.add(sem)
    db.commit()
    db.refresh(sem)

    sec_a = Section(name="A", student_count=40, semester_id=sem.id, programme_id=prog.id)
    sec_b = Section(name="B", student_count=40, semester_id=sem.id, programme_id=prog.id)
    fac = Faculty(
        faculty_id="FAC_PHY_01",
        full_name="Prof. Richard Feynman",
        email="feynman@example.edu",
        department_id=dept.id,
        max_classes_per_day=4,
        max_classes_per_week=20,
        password_hash=hash_password("feynman2026")
    )
    subj1 = Subject(
        code="PHY101",
        name="Quantum Mechanics",
        session_type=SessionType.LECTURE,
        default_duration=60,
        department_id=dept.id,
        programme_id=prog.id,
        semester_id=sem.id
    )
    subj2 = Subject(
        code="PHY102",
        name="Electromagnetism",
        session_type=SessionType.LECTURE,
        default_duration=60,
        department_id=dept.id,
        programme_id=prog.id,
        semester_id=sem.id
    )
    bld = Building(name="Einstein Hall", code="EH", available=True)
    db.add_all([sec_a, sec_b, fac, subj1, subj2, bld])
    db.commit()
    db.refresh(bld)

    flr = Floor(name="Floor 1", level=1, building_id=bld.id)
    db.add(flr)
    db.commit()
    db.refresh(flr)

    room = Room(name="Hall 101", room_type=RoomType.CLASSROOM, capacity=60, floor_id=flr.id, available=True)
    db.add(room)
    db.commit()
    db.refresh(room)

    asgn_a = FacultyAssignment(
        faculty_id=fac.id,
        subject_id=subj1.id,
        section_id=sec_a.id,
        sessions_per_week=2,
        duration_minutes=60,
        required_room_type=RoomType.CLASSROOM,
        active=True
    )
    asgn_b = FacultyAssignment(
        faculty_id=fac.id,
        subject_id=subj2.id,
        section_id=sec_b.id,
        sessions_per_week=2,
        duration_minutes=60,
        required_room_type=RoomType.CLASSROOM,
        active=True
    )
    db.add_all([asgn_a, asgn_b])
    db.commit()

    # Schedule university-wide (both sections together)
    scheduler = HybridScheduler(db, weekdays=[0, 1], day_start=540, day_end=720)
    res = scheduler.solve()
    assert res["status"] in ("OPTIMAL", "FEASIBLE")

    feynman_classes = [c for c in res["classes"] if c["faculty_id"] == fac.id]
    assert len(feynman_classes) == 4  # 2 for Sec A + 2 for Sec B

    # Verify no double booking across sections on any day
    by_day = {}
    for c in feynman_classes:
        by_day.setdefault(c["weekday"], []).append(c)

    for day, day_cls in by_day.items():
        sorted_cls = sorted(day_cls, key=lambda x: x["start_minute"])
        for i in range(len(sorted_cls) - 1):
            assert sorted_cls[i]["end_minute"] <= sorted_cls[i + 1]["start_minute"], (
                f"Double booking detected for faculty on day {day}: "
                f"{sorted_cls[i]} overlaps with {sorted_cls[i+1]}"
            )

