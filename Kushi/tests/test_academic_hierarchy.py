"""
Unit and Integration Tests for Academic Hierarchy, Student Enrolment,
Safe Deletions, Section-Specific Scheduling, and Timetable Download Auth.
"""

import pytest
from datetime import date, datetime
from fastapi.testclient import TestClient

from app.main import app
from app.models import (
    Admin, Department, Programme, AcademicYear, Semester, Section,
    Subject, Student, Faculty, FacultyAssignment, Room, Floor, Building,
    RoomType, SessionType, ScheduledClass, TimetableVersion, VersionStatus,
    Enrolment, TimetableImage
)
from app.security import hash_password, create_access_token
from app.services.scheduler import HybridScheduler
from app.services.image_generator import generate_timetable_png


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
        username="hier_admin",
        email="hier_admin@example.edu",
        password_hash=hash_password("SuperSecretAdmin123!")
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    app.dependency_overrides[get_current_admin] = lambda: admin
    token = create_access_token(admin.id)
    return {"Authorization": f"Bearer {token}"}


# ============================================================================
# 1. ACADEMIC HIERARCHY & DERIVED PROGRAMME YEAR
# ============================================================================
def test_academic_hierarchy_derivation(db, test_client, auth_headers):
    # Department
    dept_res = test_client.post("/api/academic/departments", json={
        "name": "Computer Science & Engineering",
        "code": "CSE",
        "description": "Department of CSE"
    }, headers=auth_headers)
    assert dept_res.status_code == 200
    dept_id = dept_res.json()["id"]

    # Programme
    prog_res = test_client.post("/api/academic/programmes", json={
        "department_id": dept_id,
        "name": "B.Tech Computer Science",
        "code": "BTECH-CSE",
        "duration_years": 4
    }, headers=auth_headers)
    assert prog_res.status_code == 200
    prog_id = prog_res.json()["id"]

    # Academic Year
    ay_res = test_client.post("/api/academic/academic-years", json={
        "name": "2026-2027",
        "start_date": "2026-08-01",
        "end_date": "2027-05-31"
    }, headers=auth_headers)
    assert ay_res.status_code == 200
    ay_id = ay_res.json()["id"]

    # Semesters 1 to 4 with independent section counts:
    # Sem 1: 2 sections (A, B) -> Programme Year 1
    # Sem 2: 2 sections (A, B) -> Programme Year 1
    # Sem 3: 3 sections (A, B, C) -> Programme Year 2
    # Sem 4: 2 sections (A, B) -> Programme Year 2
    for sem_num in [1, 2, 3, 4]:
        sem_res = test_client.post(
            f"/api/academic/semesters?programme_id={prog_id}&academic_year_id={ay_id}&number={sem_num}",
            headers=auth_headers
        )
        assert sem_res.status_code == 200

    # Verify derived programme year on GET /api/academic/semesters
    sem_list = test_client.get(f"/api/academic/semesters?programme_id={prog_id}", headers=auth_headers).json()
    assert len(sem_list) == 4
    for s in sem_list:
        expected_year = (s["number"] + 1) // 2
        assert s["programme_year"] == expected_year

    # Independent sections per semester
    sem1 = next(s for s in sem_list if s["number"] == 1)
    sem3 = next(s for s in sem_list if s["number"] == 3)

    # Add 2 sections to Sem 1
    test_client.post("/api/academic/sections", json={
        "programme_id": prog_id, "semester_id": sem1["id"], "name": "A", "student_count": 45
    }, headers=auth_headers)
    test_client.post("/api/academic/sections", json={
        "programme_id": prog_id, "semester_id": sem1["id"], "name": "B", "student_count": 40
    }, headers=auth_headers)

    # Add 3 sections to Sem 3
    test_client.post("/api/academic/sections", json={
        "programme_id": prog_id, "semester_id": sem3["id"], "name": "A", "student_count": 50
    }, headers=auth_headers)
    test_client.post("/api/academic/sections", json={
        "programme_id": prog_id, "semester_id": sem3["id"], "name": "B", "student_count": 48
    }, headers=auth_headers)
    test_client.post("/api/academic/sections", json={
        "programme_id": prog_id, "semester_id": sem3["id"], "name": "C", "student_count": 42
    }, headers=auth_headers)

    # Query sections filtered by semester
    sec_sem1 = test_client.get(f"/api/academic/sections?semester_id={sem1['id']}", headers=auth_headers).json()
    assert len(sec_sem1) == 2
    assert sec_sem1[0]["programme_year"] == 1

    sec_sem3 = test_client.get(f"/api/academic/sections?semester_id={sem3['id']}", headers=auth_headers).json()
    assert len(sec_sem3) == 3
    assert sec_sem3[0]["programme_year"] == 2


# ============================================================================
# 2. STUDENT ENROLMENT, TRANSFER & ACADEMIC ASSIGNMENT PROFILE
# ============================================================================
def test_student_enrolment_and_transfer(db, test_client, auth_headers):
    dept = Department(name="Information Technology", code="IT")
    db.add(dept)
    db.flush()

    prog = Programme(department_id=dept.id, name="B.Tech IT", code="BTECH-IT", duration_years=4)
    db.add(prog)
    db.flush()

    ay = AcademicYear(name="2026-2027-IT", start_date=date(2026, 8, 1), end_date=date(2027, 5, 31), active=True)
    db.add(ay)
    db.flush()

    sem = Semester(programme_id=prog.id, academic_year_id=ay.id, number=3)
    db.add(sem)
    db.flush()

    sec_a = Section(programme_id=prog.id, semester_id=sem.id, name="A", student_count=0)
    sec_b = Section(programme_id=prog.id, semester_id=sem.id, name="B", student_count=0)
    db.add_all([sec_a, sec_b])
    db.commit()

    # 1. Create student and auto-enrol in Section A
    res = test_client.post("/api/academic/students", json={
        "full_name": "Alice Wonderland",
        "email": "alice@it.edu",
        "admission_year": 2025,
        "department_id": dept.id,
        "programme_id": prog.id,
        "section_id": sec_a.id
    }, headers=auth_headers)
    assert res.status_code == 200
    student_data = res.json()
    student_id = student_data["id"]

    # Verify enrolment in Sec A
    enrolments = db.query(Enrolment).filter(Enrolment.student_id == student_id).all()
    assert len(enrolments) == 1
    assert enrolments[0].section_id == sec_a.id
    assert enrolments[0].active is True

    # Check updated section count
    db.refresh(sec_a)
    assert sec_a.student_count >= 1

    # 2. Transfer student from Section A to Section B
    trans_res = test_client.post(f"/api/academic/students/{student_id}/transfer", json={
        "new_section_id": sec_b.id
    }, headers=auth_headers)
    assert trans_res.status_code == 200
    assert trans_res.json()["status"] == "TRANSFERRED"

    # Verify no duplicate active enrolments
    active_enrolments = db.query(Enrolment).filter(
        Enrolment.student_id == student_id,
        Enrolment.active.is_(True)
    ).all()
    assert len(active_enrolments) == 1
    assert active_enrolments[0].section_id == sec_b.id

    # Old enrolment must be inactive
    old_enr = db.query(Enrolment).filter(
        Enrolment.student_id == student_id,
        Enrolment.section_id == sec_a.id
    ).first()
    assert old_enr.active is False

    # 3. View complete academic assignment
    profile_res = test_client.get(f"/api/academic/students/{student_id}/assignment", headers=auth_headers)
    assert profile_res.status_code == 200
    profile = profile_res.json()
    assert profile["student"]["full_name"] == "Alice Wonderland"
    assert profile["programme"]["code"] == "BTECH-IT"
    assert profile["section"]["name"] == "B"
    assert profile["student"]["current_year"] == 2  # Semester 3 -> ceil(3/2) = Year 2


# ============================================================================
# 3. SUBJECT MANAGEMENT & SAFE DELETION
# ============================================================================
def test_subject_management_and_safe_deletion(db, test_client, auth_headers):
    dept = Department(name="Civil Engineering", code="CE")
    db.add(dept)
    db.flush()

    prog = Programme(department_id=dept.id, name="B.Tech CE", code="BTECH-CE", duration_years=4)
    db.add(prog)
    db.flush()

    ay = AcademicYear(name="2026-2027-CE", start_date=date(2026, 8, 1), end_date=date(2027, 5, 31))
    db.add(ay)
    db.flush()

    sem = Semester(programme_id=prog.id, academic_year_id=ay.id, number=1)
    db.add(sem)
    db.flush()

    sec = Section(programme_id=prog.id, semester_id=sem.id, name="A")
    db.add(sec)
    db.flush()

    fac = Faculty(faculty_id="CE-FAC-99", department_id=dept.id, full_name="Dr. Concrete", email="concrete@ce.edu")
    db.add(fac)
    db.commit()

    # 1. Create subject tied to programme and semester
    sub_res = test_client.post("/api/academic/subjects", json={
        "department_id": dept.id,
        "programme_id": prog.id,
        "semester_number": 1,
        "code": "CE-101",
        "name": "Structural Analysis",
        "session_type": "LECTURE",
        "default_duration": 60
    }, headers=auth_headers)
    assert sub_res.status_code == 200
    sub_id = sub_res.json()["id"]

    # 2. Duplicate code in same programme and semester must be rejected (HTTP 409)
    dup_res = test_client.post("/api/academic/subjects", json={
        "department_id": dept.id,
        "programme_id": prog.id,
        "semester_number": 1,
        "code": "CE-101",
        "name": "Duplicate Subject",
        "session_type": "LECTURE",
        "default_duration": 60
    }, headers=auth_headers)
    assert dup_res.status_code == 409

    # 3. Associate subject with a FacultyAssignment
    fa = FacultyAssignment(
        faculty_id=fac.id,
        subject_id=sub_id,
        section_id=sec.id,
        sessions_per_week=3,
        duration_minutes=60,
        required_room_type=RoomType.CLASSROOM
    )
    db.add(fa)
    db.commit()

    # 4. Safe deletion check: attempting to delete subject must fail with 400
    del_res = test_client.delete(f"/api/academic/subjects/{sub_id}", headers=auth_headers)
    assert del_res.status_code == 400
    assert "referenced by 1 faculty assignments" in del_res.json()["detail"]

    # 5. Remove assignment and delete safely
    db.delete(fa)
    db.commit()
    del_ok = test_client.delete(f"/api/academic/subjects/{sub_id}", headers=auth_headers)
    assert del_ok.status_code == 200
    assert del_ok.json()["status"] == "DELETED"


# ============================================================================
# 4. PROGRAMME CRUD & SAFE DELETION
# ============================================================================
def test_programme_safe_deletion(db, test_client, auth_headers):
    dept = Department(name="Chemical Engineering", code="CHEM")
    db.add(dept)
    db.flush()

    prog = Programme(department_id=dept.id, name="B.Tech Chemical", code="BTECH-CHEM", duration_years=4)
    db.add(prog)
    db.flush()

    ay = AcademicYear(name="2026-2027-CHEM", start_date=date(2026, 8, 1), end_date=date(2027, 5, 31))
    db.add(ay)
    db.flush()

    sem = Semester(programme_id=prog.id, academic_year_id=ay.id, number=1)
    db.add(sem)
    db.commit()

    # Deletion blocked because dependent semester exists
    del_res = test_client.delete(f"/api/academic/programmes/{prog.id}", headers=auth_headers)
    assert del_res.status_code == 400
    assert "It has 1 semesters" in del_res.json()["detail"]

    # Delete semester first, then programme deletion succeeds
    db.delete(sem)
    db.commit()

    del_ok = test_client.delete(f"/api/academic/programmes/{prog.id}", headers=auth_headers)
    assert del_ok.status_code == 200
    assert del_ok.json()["status"] == "DELETED"


# ============================================================================
# 5. SECTION-SPECIFIC TIMETABLE GENERATION & CLASH AVOIDANCE
# ============================================================================
def test_section_specific_scheduling_and_conflict_avoidance(db):
    dept = Department(name="BioTech", code="BT")
    db.add(dept)
    db.flush()

    prog = Programme(department_id=dept.id, name="B.Tech BioTech", code="BTECH-BT", duration_years=4)
    db.add(prog)
    db.flush()

    ay = AcademicYear(name="2026-2027-BT", start_date=date(2026, 8, 1), end_date=date(2027, 5, 31), active=True)
    db.add(ay)
    db.flush()

    sem = Semester(programme_id=prog.id, academic_year_id=ay.id, number=1)
    db.add(sem)
    db.flush()

    sec_a = Section(programme_id=prog.id, semester_id=sem.id, name="Sec-A", student_count=30)
    sec_b = Section(programme_id=prog.id, semester_id=sem.id, name="Sec-B", student_count=30)
    db.add_all([sec_a, sec_b])
    db.flush()

    sub = Subject(department_id=dept.id, programme_id=prog.id, semester_number=1, code="BT-101", name="Genetics", session_type=SessionType.LECTURE, default_duration=60)
    db.add(sub)
    db.flush()

    # Shared faculty and shared classroom
    fac = Faculty(faculty_id="BT-FAC-01", department_id=dept.id, full_name="Dr. Mendel", email="mendel@bt.edu")
    bldg = Building(name="Bio Building", code="BB")
    db.add_all([fac, bldg])
    db.flush()

    floor = Floor(building_id=bldg.id, name="F1", level=1)
    db.add(floor)
    db.flush()

    room = Room(floor_id=floor.id, name="Lab-101", room_type=RoomType.CLASSROOM, capacity=40)
    db.add(room)
    db.flush()

    # Assignment for Sec A
    assign_a = FacultyAssignment(
        faculty_id=fac.id, subject_id=sub.id, section_id=sec_a.id,
        sessions_per_week=1, duration_minutes=60, required_room_type=RoomType.CLASSROOM
    )
    # Assignment for Sec B with SAME teacher and SAME room
    assign_b = FacultyAssignment(
        faculty_id=fac.id, subject_id=sub.id, section_id=sec_b.id,
        sessions_per_week=1, duration_minutes=60, required_room_type=RoomType.CLASSROOM
    )
    db.add_all([assign_a, assign_b])
    db.commit()

    # 1. Schedule Section A specifically
    scheduler_a = HybridScheduler(db, section_id=sec_a.id, weekdays=[0], day_start=480, day_end=600)
    res_a = scheduler_a.solve()
    assert res_a["status"] in ("OPTIMAL", "FEASIBLE")
    assert len(res_a["classes"]) == 1
    class_a = res_a["classes"][0]

    # Save and publish Section A's timetable
    ver_a = TimetableVersion(
        version_number=1, status=VersionStatus.PUBLISHED, algorithm="HYBRID",
        section_id=sec_a.id, quality_score=100
    )
    db.add(ver_a)
    db.flush()
    db.add(ScheduledClass(
        version_id=ver_a.id,
        assignment_id=assign_a.id,
        faculty_id=fac.id,
        section_id=sec_a.id,
        subject_id=sub.id,
        room_id=room.id,
        weekday=class_a["weekday"],
        start_minute=class_a["start_minute"],
        end_minute=class_a["end_minute"],
        session_number=1
    ))
    db.commit()

    # 2. Schedule Section B specifically
    # Scheduler must inspect published version of Section A and avoid the slot (class_a["start_minute"] to class_a["end_minute"])
    scheduler_b = HybridScheduler(db, section_id=sec_b.id, weekdays=[0], day_start=480, day_end=600)
    res_b = scheduler_b.solve()
    assert res_b["status"] in ("OPTIMAL", "FEASIBLE")
    assert len(res_b["classes"]) == 1
    class_b = res_b["classes"][0]

    # Confirm NO overlap for the shared faculty and room
    a_start, a_end = class_a["start_minute"], class_a["end_minute"]
    b_start, b_end = class_b["start_minute"], class_b["end_minute"]
    overlap = max(0, min(a_end, b_end) - max(a_start, b_start))
    assert overlap == 0, f"Clash detected between Section A [{a_start}-{a_end}] and Section B [{b_start}-{b_end}]!"


# ============================================================================
# 6. TIMETABLE DOWNLOAD AUTHENTICATION
# ============================================================================
def test_timetable_download_authentication(db, test_client, auth_headers):
    dept = Department(name="Math Dept", code="MATH")
    db.add(dept)
    db.flush()

    prog = Programme(department_id=dept.id, name="B.Sc Math", code="BSC-MATH", duration_years=3)
    db.add(prog)
    db.flush()

    ay = AcademicYear(name="2026-2027-MATH", start_date=date(2026, 8, 1), end_date=date(2027, 5, 31))
    db.add(ay)
    db.flush()

    sem = Semester(programme_id=prog.id, academic_year_id=ay.id, number=1)
    db.add(sem)
    db.flush()

    sec = Section(programme_id=prog.id, semester_id=sem.id, name="A")
    db.add(sec)
    db.flush()

    ver = TimetableVersion(version_number=10, status=VersionStatus.APPROVED, algorithm="HYBRID")
    db.add(ver)
    db.flush()

    # Generate image for Sec A
    img = generate_timetable_png(db, ver.id, "STUDENT", sec.id)
    db.commit()

    # 1. Unauthenticated download request should be rejected with 401
    from app.dependencies import get_current_admin
    app.dependency_overrides.pop(get_current_admin, None)
    unauth_res = test_client.get(f"/api/scheduling/images/{img.id}/download")
    assert unauth_res.status_code == 401

    # 2. Authenticated download request with Bearer token succeeds with PNG image
    admin = db.query(Admin).first()
    app.dependency_overrides[get_current_admin] = lambda: admin
    auth_res = test_client.get(f"/api/scheduling/images/{img.id}/download", headers=auth_headers)
    assert auth_res.status_code == 200
    assert auth_res.headers["content-type"] == "image/png"
    assert len(auth_res.content) > 0
