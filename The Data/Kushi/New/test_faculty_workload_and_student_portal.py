from datetime import date
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import get_db
from app.models import (
    Admin, Department, Programme, AcademicYear, Semester, Section, Subject,
    Faculty, FacultyAssignment, Student, Enrolment, Room, Floor, Building,
    SessionType, RoomType, TimetableVersion, VersionStatus, ScheduledClass
)
from app.services.scheduler import HybridScheduler
from app.security import hash_password, create_access_token


@pytest.fixture
def client(db):
    app.dependency_overrides[get_db] = lambda: db
    c = TestClient(app)
    yield c
    app.dependency_overrides.clear()


@pytest.fixture
def admin_headers(db):
    admin = Admin(
        username="workload_admin",
        email="workload_admin@example.edu",
        password_hash=hash_password("SuperSecretAdmin123!")
    )
    db.add(admin)
    db.commit()
    token = create_access_token(admin.id, role="ADMIN")
    return {"Authorization": f"Bearer {token}"}


def test_six_day_timetable_scheduling(db):
    """
    Test 1: Six-day scheduling allocation.
    Verifies that when weekdays=[0, 1, 2, 3, 4, 5] (Monday to Saturday) are selected,
    the CP-SAT solver successfully schedules classes on Saturday (weekday 5).
    Verifies that 5-day scheduling does not allocate classes to Saturday.
    """
    dept = Department(name="Computer Science 6Day", code="CS6D")
    db.add(dept)
    db.flush()

    prog = Programme(name="B.Tech Computer Science 6D", code="BTECH-6D", department_id=dept.id)
    db.add(prog)
    db.flush()

    ay = AcademicYear(name="2026-6DAY", start_date=date(2026, 1, 1), end_date=date(2026, 12, 31), active=True)
    db.add(ay)
    db.flush()

    sem = Semester(programme_id=prog.id, academic_year_id=ay.id, number=1)
    db.add(sem)
    db.flush()

    sec = Section(semester_id=sem.id, programme_id=prog.id, name="A", student_count=30)
    db.add(sec)
    db.flush()

    fac = Faculty(
        faculty_id="FAC-6D-01",
        department_id=dept.id,
        full_name="Prof. Saturday Scheduler",
        email="sat@example.edu",
        max_classes_per_day=4,
        max_classes_per_week=24
    )
    db.add(fac)
    db.flush()

    bld = Building(name="Bld 6D", code="B6D")
    db.add(bld)
    db.flush()
    flr = Floor(building_id=bld.id, name="F1", level=1)
    db.add(flr)
    db.flush()
    rm = Room(floor_id=flr.id, name="Room 6D", room_type=RoomType.CLASSROOM, capacity=50)
    db.add(rm)
    db.flush()

    # Create 3 subjects with 4 sessions per week each = 12 sessions total
    for i in range(1, 4):
        sub = Subject(
            department_id=dept.id,
            programme_id=prog.id,
            semester_number=1,
            code=f"CS6D-0{i}",
            name=f"Course 6D 0{i}",
            session_type=SessionType.LECTURE
        )
        db.add(sub)
        db.flush()

        assign = FacultyAssignment(
            faculty_id=fac.id,
            subject_id=sub.id,
            section_id=sec.id,
            sessions_per_week=4,
            duration_minutes=60,
            priority=8,
            required_capacity=30,
            required_room_type=RoomType.CLASSROOM
        )
        db.add(assign)

    db.commit()

    # 1. Test with 6 working days (Monday=0 through Saturday=5)
    scheduler_6d = HybridScheduler(
        db,
        weekdays=[0, 1, 2, 3, 4, 5],
        day_start=480,
        day_end=720,  # 8am to 12pm (4 slots/day)
        section_id=sec.id
    )
    res_6d = scheduler_6d.solve()
    assert res_6d["status"] in ("OPTIMAL", "FEASIBLE")
    weekdays_used = set(c["weekday"] for c in res_6d["classes"])
    assert 5 in weekdays_used, "Saturday (weekday 5) must be actively allocated classes in 6-day mode"

    # 2. Test with 5 working days (Monday=0 through Friday=4)
    scheduler_5d = HybridScheduler(
        db,
        weekdays=[0, 1, 2, 3, 4],
        day_start=480,
        day_end=780,
        section_id=sec.id
    )
    res_5d = scheduler_5d.solve()
    assert res_5d["status"] in ("OPTIMAL", "FEASIBLE")
    weekdays_used_5d = set(c["weekday"] for c in res_5d["classes"])
    assert 5 not in weekdays_used_5d, "Saturday must NOT be scheduled when 5-day mode is selected"


def test_faculty_department_and_cross_department_exception(client, admin_headers, db):
    """
    Test 2: Teaching eligibility department restriction and exception approval.
    """
    dept_cs = Department(name="Computer Science Dept", code="CSDEPT")
    dept_ee = Department(name="Electrical Engineering Dept", code="EEDEPT")
    db.add_all([dept_cs, dept_ee])
    db.flush()

    prog_cs = Programme(name="B.Tech CSE", code="BCSE-T", department_id=dept_cs.id)
    db.add(prog_cs)
    db.flush()

    ay = AcademicYear(name="2026-TDEP", start_date=date(2026, 1, 1), end_date=date(2026, 12, 31), active=True)
    db.add(ay)
    db.flush()

    sem = Semester(programme_id=prog_cs.id, academic_year_id=ay.id, number=1)
    db.add(sem)
    db.flush()

    sec = Section(semester_id=sem.id, programme_id=prog_cs.id, name="A")
    db.add(sec)
    db.flush()

    # Subject belongs to Electrical Engineering
    sub_ee = Subject(
        department_id=dept_ee.id,
        programme_id=prog_cs.id,
        code="EE-101",
        name="Basic Electrical Circuits",
        session_type=SessionType.LECTURE
    )
    db.add(sub_ee)
    db.flush()

    # Faculty belongs to Computer Science (cross_department_approved = False)
    fac_cs = Faculty(
        faculty_id="FAC-CS-RESTRICTED",
        department_id=dept_cs.id,
        full_name="Dr. CS Specialist",
        email="cs.spec@example.edu",
        cross_department_approved=False
    )
    db.add(fac_cs)
    db.commit()

    # Attempt to assign CS faculty to EE subject without approval -> Must fail with 400
    res_reject = client.post("/api/academic/assignments", headers=admin_headers, json={
        "faculty_id": fac_cs.id,
        "subject_id": sub_ee.id,
        "section_id": sec.id,
        "sessions_per_week": 3,
        "duration_minutes": 60,
        "priority": 5,
        "required_capacity": 30,
        "required_room_type": "CLASSROOM"
    })
    assert res_reject.status_code == 400
    assert "cross-department" in res_reject.json()["detail"].lower()

    # Now approve cross-department teaching exception for this faculty
    res_elig = client.post(f"/api/academic/faculty/{fac_cs.id}/eligibility", headers=admin_headers, json={
        "subject_ids": [sub_ee.id],
        "eligible_semesters": [1, 2],
        "cross_department_approved": True
    })
    assert res_elig.status_code == 200
    assert res_elig.json()["cross_department_approved"] is True

    # Retry assignment -> Must now succeed with 200
    res_success = client.post("/api/academic/assignments", headers=admin_headers, json={
        "faculty_id": fac_cs.id,
        "subject_id": sub_ee.id,
        "section_id": sec.id,
        "sessions_per_week": 3,
        "duration_minutes": 60,
        "priority": 5,
        "required_capacity": 30,
        "required_room_type": "CLASSROOM"
    })
    assert res_success.status_code == 200


def test_faculty_workload_hard_constraints_and_overview(client, admin_headers, db):
    """
    Test 3: Faculty workload safety limits (daily, weekly, consecutive) and workload analytics endpoint.
    """
    dept = Department(name="Mechanical Eng", code="MECH")
    db.add(dept)
    db.flush()

    fac = Faculty(
        faculty_id="FAC-WORKLOAD-01",
        department_id=dept.id,
        full_name="Prof. Heavy Worker",
        email="heavy@example.edu",
        designation="Associate Professor",
        highest_qualification="Ph.D. in Thermal Science",
        specialisation="Thermodynamics",
        max_classes_per_day=3,
        max_classes_per_week=6,  # Cap at 6 weekly sessions
        max_consecutive_hours=2,
        min_break_minutes=15
    )
    db.add(fac)
    db.flush()

    prog = Programme(name="B.Tech ME", code="BME", department_id=dept.id)
    db.add(prog)
    db.flush()
    ay = AcademicYear(name="2026-ME", start_date=date(2026, 1, 1), end_date=date(2026, 12, 31), active=True)
    db.add(ay)
    db.flush()
    sem = Semester(programme_id=prog.id, academic_year_id=ay.id, number=3)
    db.add(sem)
    db.flush()
    sec = Section(semester_id=sem.id, programme_id=prog.id, name="A")
    db.add(sec)
    db.flush()

    sub = Subject(department_id=dept.id, programme_id=prog.id, code="ME-301", name="Thermodynamics", session_type=SessionType.LECTURE)
    db.add(sub)
    db.commit()

    # Attempt to assign 8 weekly sessions when faculty max is 6 -> Must be rejected
    res_overload = client.post("/api/academic/assignments", headers=admin_headers, json={
        "faculty_id": fac.id,
        "subject_id": sub.id,
        "section_id": sec.id,
        "sessions_per_week": 8,
        "duration_minutes": 60,
        "priority": 5,
        "required_capacity": 30,
        "required_room_type": "CLASSROOM"
    })
    assert res_overload.status_code == 400
    assert "workload limit exceeded" in res_overload.json()["detail"].lower()

    # Assign 5 sessions (within 6 limit) -> Succeeds
    res_ok = client.post("/api/academic/assignments", headers=admin_headers, json={
        "faculty_id": fac.id,
        "subject_id": sub.id,
        "section_id": sec.id,
        "sessions_per_week": 5,
        "duration_minutes": 60,
        "priority": 5,
        "required_capacity": 30,
        "required_room_type": "CLASSROOM"
    })
    assert res_ok.status_code == 200

    # Verify Faculty Workload Overview endpoint
    res_wl = client.get("/api/academic/faculty-workload/overview", headers=admin_headers)
    assert res_wl.status_code == 200
    data = res_wl.json()
    assert "faculty_workload" in data
    assert "department_distribution" in data
    fac_entry = next((f for f in data["faculty_workload"] if f["faculty_id"] == fac.id), None)
    assert fac_entry is not None
    assert fac_entry["max_classes_per_week"] == 6
    assert fac_entry["assigned_sessions_per_week"] == 5
    assert fac_entry["remaining_available_workload"] == 1


def test_student_portal_authentication_and_access_control(client, admin_headers, db):
    """
    Test 4: Dedicated student authentication, access control separation,
    and section timetable viewing restrictions.
    """
    dept = Department(name="IT Dept", code="ITD")
    db.add(dept)
    db.flush()

    prog = Programme(name="B.Tech IT", code="BIT", department_id=dept.id)
    db.add(prog)
    db.flush()

    ay = AcademicYear(name="2026-IT", start_date=date(2026, 1, 1), end_date=date(2026, 12, 31), active=True)
    db.add(ay)
    db.flush()

    sem = Semester(programme_id=prog.id, academic_year_id=ay.id, number=1)
    db.add(sem)
    db.flush()

    sec_a = Section(semester_id=sem.id, programme_id=prog.id, name="A")
    sec_b = Section(semester_id=sem.id, programme_id=prog.id, name="B")
    db.add_all([sec_a, sec_b])
    db.flush()

    student = Student(
        student_id="STU2026999",
        full_name="Alice Student",
        email="alice@student.edu",
        admission_year=2026,
        department_id=dept.id,
        programme_id=prog.id,
        current_year=1,
        current_semester=1,
        password_hash=hash_password("student_pass123")
    )
    db.add(student)
    db.flush()

    enr = Enrolment(student_id=student.id, section_id=sec_a.id, active=True)
    db.add(enr)
    db.commit()

    # 1. Student Login
    res_login = client.post("/api/auth/student-login", json={
        "identifier": "STU2026999",
        "password": "student_pass123"
    })
    assert res_login.status_code == 200
    student_token = res_login.json()["access_token"]
    student_headers = {"Authorization": f"Bearer {student_token}"}

    # 2. Student Profile Endpoint
    res_prof = client.get("/api/student/profile", headers=student_headers)
    assert res_prof.status_code == 200
    prof_data = res_prof.json()
    assert prof_data["student"]["student_id"] == "STU2026999"
    assert prof_data["section"]["name"] == "A"
    assert prof_data["programme"]["code"] == "BIT"

    # 3. Security Check: Student CANNOT call admin endpoints
    res_forbidden = client.post("/api/academic/departments", headers=student_headers, json={
        "name": "Hacked Dept",
        "code": "HACK"
    })
    assert res_forbidden.status_code in (401, 403), "Students must be rejected from administrative endpoints"

    # 4. Student Timetable endpoint returns proper section status
    res_tt = client.get("/api/student/timetable", headers=student_headers)
    assert res_tt.status_code == 200
    assert res_tt.json()["status"] in ("PUBLISHED", "NO_PUBLISHED_TIMETABLE")


def test_consecutive_classes_and_daily_limits(db):
    """
    Test 5: Scheduler hard constraints for maximum daily classes and max consecutive hours.
    Ensures that CP-SAT solver does not schedule more than max_classes_per_day,
    and does not exceed max_consecutive_hours.
    """
    dept = Department(name="Physics Dept", code="PHYS")
    db.add(dept)
    db.flush()

    prog = Programme(name="B.Sc Physics", code="BSCP", department_id=dept.id)
    db.add(prog)
    db.flush()

    ay = AcademicYear(name="2026-PHYS", start_date=date(2026, 1, 1), end_date=date(2026, 12, 31), active=True)
    db.add(ay)
    db.flush()

    sem = Semester(programme_id=prog.id, academic_year_id=ay.id, number=1)
    db.add(sem)
    db.flush()

    sec = Section(semester_id=sem.id, programme_id=prog.id, name="A")
    db.add(sec)
    db.flush()

    fac = Faculty(
        faculty_id="FAC-PHYS-01",
        department_id=dept.id,
        full_name="Dr. Strict Limits",
        email="limits@example.edu",
        max_classes_per_day=2,      # Hard limit: max 2 classes per day
        max_classes_per_week=10,
        max_consecutive_hours=1     # Hard limit: no 2 consecutive hours without break
    )
    db.add(fac)
    db.flush()

    bld = Building(name="Phys Bld", code="PB")
    db.add(bld)
    db.flush()
    flr = Floor(building_id=bld.id, name="F1", level=1)
    db.add(flr)
    db.flush()
    rm = Room(floor_id=flr.id, name="Lab P1", room_type=RoomType.CLASSROOM, capacity=40)
    db.add(rm)
    db.flush()

    # Create 2 subjects with 4 sessions total (e.g. 2 each)
    sub1 = Subject(department_id=dept.id, programme_id=prog.id, semester_number=1, code="PH-101", name="Mechanics", session_type=SessionType.LECTURE)
    sub2 = Subject(department_id=dept.id, programme_id=prog.id, semester_number=1, code="PH-102", name="Optics", session_type=SessionType.LECTURE)
    db.add_all([sub1, sub2])
    db.flush()

    db.add(FacultyAssignment(
        faculty_id=fac.id,
        subject_id=sub1.id,
        section_id=sec.id,
        sessions_per_week=2,
        duration_minutes=60,
        priority=8,
        required_capacity=30,
        required_room_type=RoomType.CLASSROOM
    ))
    db.add(FacultyAssignment(
        faculty_id=fac.id,
        subject_id=sub2.id,
        section_id=sec.id,
        sessions_per_week=2,
        duration_minutes=60,
        priority=8,
        required_capacity=30,
        required_room_type=RoomType.CLASSROOM
    ))
    db.commit()

    # Solve across 5 working days with day 8am to 2pm (6 slots/day)
    scheduler = HybridScheduler(
        db,
        weekdays=[0, 1, 2, 3, 4],
        day_start=480,
        day_end=840,
        section_id=sec.id
    )
    res = scheduler.solve()
    assert res["status"] in ("OPTIMAL", "FEASIBLE")

    # Check daily limits for this faculty
    classes_by_day = {}
    for c in res["classes"]:
        if c["faculty_id"] == fac.id:
            d = c["weekday"]
            classes_by_day.setdefault(d, []).append(c)

    for d, day_classes in classes_by_day.items():
        assert len(day_classes) <= fac.max_classes_per_day, (
            f"Day {d} had {len(day_classes)} classes, exceeding max_classes_per_day of {fac.max_classes_per_day}"
        )
        # Check max consecutive hours: since max_consecutive_hours=1, no two classes can be adjacent
        day_classes.sort(key=lambda x: x["start_minute"])
        for idx in range(len(day_classes) - 1):
            curr_end = day_classes[idx]["end_minute"]
            next_start = day_classes[idx + 1]["start_minute"]
            assert next_start > curr_end, (
                f"Consecutive classes found on day {d} without required break"
            )


def test_png_timetable_download_and_draft_privacy(client, admin_headers, db):
    """
    Test 6: Verify direct section PNG download endpoint and student portal download.
    Ensure draft timetable images are not publicly accessible to students,
    while published versions are properly downloadable.
    """
    dept = Department(name="Bio Dept", code="BIO")
    db.add(dept)
    db.flush()

    prog = Programme(name="B.Tech Biotech", code="BBIO", department_id=dept.id)
    db.add(prog)
    db.flush()

    ay = AcademicYear(name="2026-BIO", start_date=date(2026, 1, 1), end_date=date(2026, 12, 31), active=True)
    db.add(ay)
    db.flush()

    sem = Semester(programme_id=prog.id, academic_year_id=ay.id, number=1)
    db.add(sem)
    db.flush()

    sec = Section(semester_id=sem.id, programme_id=prog.id, name="A")
    db.add(sec)
    db.flush()

    bld = Building(name="Bio Bld", code="BB")
    db.add(bld)
    db.flush()
    flr = Floor(building_id=bld.id, name="F1", level=1)
    db.add(flr)
    db.flush()
    rm = Room(floor_id=flr.id, name="Lab B1", room_type=RoomType.CLASSROOM, capacity=40)
    db.add(rm)
    db.flush()

    fac = Faculty(
        faculty_id="FAC-BIO-01",
        department_id=dept.id,
        full_name="Dr. Bio Teacher",
        email="bio@example.edu"
    )
    db.add(fac)
    db.flush()

    sub = Subject(department_id=dept.id, programme_id=prog.id, semester_number=1, code="BIO-101", name="Biochemistry", session_type=SessionType.LECTURE)
    db.add(sub)
    db.flush()

    assign = FacultyAssignment(
        faculty_id=fac.id,
        subject_id=sub.id,
        section_id=sec.id,
        sessions_per_week=1,
        duration_minutes=60,
        priority=5,
        required_capacity=30,
        required_room_type=RoomType.CLASSROOM
    )
    db.add(assign)
    db.flush()

    student = Student(
        student_id="STU2026BIO",
        full_name="Bio Student",
        email="biostudent@example.edu",
        admission_year=2026,
        department_id=dept.id,
        programme_id=prog.id,
        current_year=1,
        current_semester=1,
        password_hash=hash_password("biopass123")
    )
    db.add(student)
    db.flush()

    enr = Enrolment(student_id=student.id, section_id=sec.id, active=True)
    db.add(enr)
    db.flush()

    # Create a draft timetable version
    tv_draft = TimetableVersion(
        academic_year_id=ay.id,
        programme_id=prog.id,
        semester_id=sem.id,
        section_id=sec.id,
        version_number=1,
        status=VersionStatus.DRAFT,
        algorithm="HYBRID_CPSAT"
    )
    db.add(tv_draft)
    db.flush()

    sc = ScheduledClass(
        version_id=tv_draft.id,
        assignment_id=assign.id,
        subject_id=sub.id,
        faculty_id=fac.id,
        room_id=rm.id,
        section_id=sec.id,
        weekday=0,
        start_minute=540,
        end_minute=600,
        session_number=1
    )
    db.add(sc)
    db.commit()

    # 1. Student login
    res_login = client.post("/api/auth/student-login", json={
        "identifier": "STU2026BIO",
        "password": "biopass123"
    })
    assert res_login.status_code == 200
    student_headers = {"Authorization": f"Bearer {res_login.json()['access_token']}"}

    # 2. Draft is NOT visible to student
    res_tt_draft = client.get("/api/student/timetable", headers=student_headers)
    assert res_tt_draft.status_code == 200
    assert res_tt_draft.json()["status"] == "NO_PUBLISHED_TIMETABLE"

    # 3. Direct Section Download as Admin (draft allowed for admin)
    res_admin_dl = client.get(
        f"/api/scheduling/versions/{tv_draft.id}/section/{sec.id}/download",
        headers=admin_headers
    )
    assert res_admin_dl.status_code == 200
    assert res_admin_dl.headers["content-type"] == "image/png"
    assert "attachment" in res_admin_dl.headers.get("content-disposition", "")
    assert len(res_admin_dl.content) > 100

    # 4. Publish the version
    tv_draft.status = VersionStatus.PUBLISHED
    db.commit()

    # 5. Now student sees PUBLISHED timetable
    res_tt_pub = client.get("/api/student/timetable", headers=student_headers)
    assert res_tt_pub.status_code == 200
    assert res_tt_pub.json()["status"] == "PUBLISHED"
    assert len(res_tt_pub.json()["classes"]) == 1

    # 6. Student downloads their section PNG timetable
    res_stu_dl = client.get("/api/student/timetable/download", headers=student_headers)
    assert res_stu_dl.status_code == 200
    assert res_stu_dl.headers["content-type"] == "image/png"
    assert "attachment" in res_stu_dl.headers.get("content-disposition", "")
    assert len(res_stu_dl.content) > 100

