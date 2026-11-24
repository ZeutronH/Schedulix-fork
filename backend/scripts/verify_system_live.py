import sys
import httpx
import io
from PIL import Image

BASE_BACKEND = "http://127.0.0.1:8001"
BASE_ADMIN_UI = "http://127.0.0.1:5173"
BASE_STUDENT_UI = "http://127.0.0.1:5174"

def test_live_system():
    print("==================================================")
    print("SCHEDULIX LIVE SYSTEM END-TO-END VERIFICATION")
    print("==================================================")

    # 1. UI Status Checks
    print("\n1. Checking UI servers...")
    res_admin = httpx.get(BASE_ADMIN_UI)
    assert res_admin.status_code == 200, f"Admin UI returned {res_admin.status_code}"
    assert "Schedulix" in res_admin.text
    print("   [PASS] Dedicated Administrator Portal is active on port 5173")

    res_stu = httpx.get(BASE_STUDENT_UI)
    assert res_stu.status_code == 200, f"Student UI returned {res_stu.status_code}"
    assert "Student Timetable Portal" in res_stu.text
    print("   [PASS] Dedicated Student Portal is active on port 5174")

    # 2. Admin Authentication
    print("\n2. Authenticating as Administrator...")
    # Read admin from DB or login with default
    from app.database import SessionLocal
    from app.models import Admin, Faculty, Department, Programme, AcademicYear, Semester, Section, Subject, Student, Enrolment, TimetableVersion, ScheduledClass, VersionStatus, Room, SessionType, RoomType
    from app.security import hash_password, create_access_token

    db = SessionLocal()
    admin = db.query(Admin).first()
    if not admin:
        admin = Admin(
            username="admin",
            email="admin@schedulix.edu",
            password_hash=hash_password("Admin@123456")
        )
        db.add(admin)
        db.commit()
    admin_token = create_access_token(admin.id, role="ADMIN")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    print(f"   [PASS] Admin token generated for {admin.username} ({admin.id})")

    # 3. Faculty Workload Overview API
    print("\n3. Testing Faculty Workload Overview endpoint...")
    res_wl = httpx.get(f"{BASE_BACKEND}/api/academic/faculty-workload/overview", headers=admin_headers)
    assert res_wl.status_code == 200, f"Workload overview failed: {res_wl.status_code} {res_wl.text}"
    wl_data = res_wl.json()
    assert "faculty_workload" in wl_data
    assert "department_distribution" in wl_data
    print(f"   [PASS] Faculty workload overview returned {len(wl_data['faculty_workload'])} faculty entries and {len(wl_data['department_distribution'])} department capacity stats")

    # 4. Create or Ensure Test Data for 6-Day Schedule
    print("\n4. Verifying Six-Day Scheduling and Saturday class allocation...")
    dept = db.query(Department).filter_by(code="CS-DEMO").first()
    if not dept:
        dept = Department(name="Computer Science Demo", code="CS-DEMO")
        db.add(dept)
        db.flush()

    prog = db.query(Programme).filter_by(code="BTECH-DEMO").first()
    if not prog:
        prog = Programme(name="B.Tech Computer Science Demo", code="BTECH-DEMO", department_id=dept.id)
        db.add(prog)
        db.flush()

    from datetime import date
    ay = db.query(AcademicYear).filter_by(name="2026-DEMO").first()
    if not ay:
        ay = AcademicYear(name="2026-DEMO", start_date=date(2026, 1, 1), end_date=date(2026, 12, 31), active=True)
        db.add(ay)
        db.flush()

    sem = db.query(Semester).filter_by(programme_id=prog.id, number=1).first()
    if not sem:
        sem = Semester(programme_id=prog.id, academic_year_id=ay.id, number=1)
        db.add(sem)
        db.flush()

    sec = db.query(Section).filter_by(programme_id=prog.id, semester_id=sem.id, name="A").first()
    if not sec:
        sec = Section(semester_id=sem.id, programme_id=prog.id, name="A", student_count=40)
        db.add(sec)
        db.flush()

    # Faculty with qualifications
    fac = db.query(Faculty).filter_by(faculty_id="FAC-DEMO-01").first()
    if not fac:
        fac = Faculty(
            faculty_id="FAC-DEMO-01",
            department_id=dept.id,
            full_name="Prof. Alan Turing",
            email="turing@schedulix.edu",
            designation="Professor",
            highest_qualification="Ph.D. in Computer Science",
            specialisation="Algorithms & Computation",
            max_classes_per_day=4,
            max_classes_per_week=20,
            max_consecutive_hours=2,
            min_break_minutes=15,
            cross_department_approved=False
        )
        db.add(fac)
        db.flush()

    # Ensure there is at least one subject and assignment
    from app.models import FacultyAssignment
    sub = db.query(Subject).filter_by(code="CSD-101").first()
    if not sub:
        sub = Subject(
            department_id=dept.id,
            programme_id=prog.id,
            semester_number=1,
            code="CSD-101",
            name="Foundations of Computer Systems",
            session_type=SessionType.LECTURE
        )
        db.add(sub)
        db.flush()

    assign = db.query(FacultyAssignment).filter_by(subject_id=sub.id, section_id=sec.id).first()
    if not assign:
        assign = FacultyAssignment(
            faculty_id=fac.id,
            subject_id=sub.id,
            section_id=sec.id,
            sessions_per_week=6,
            duration_minutes=60,
            priority=8,
            required_capacity=40,
            required_room_type=RoomType.CLASSROOM
        )
        db.add(assign)
    db.commit()

    # Run scheduler directly with 6 working days (Monday-Saturday)
    from app.services.scheduler import HybridScheduler
    scheduler = HybridScheduler(
        db,
        weekdays=[0, 1, 2, 3, 4, 5],
        day_start=480,
        day_end=780,
        section_id=sec.id
    )

    res_sched = scheduler.solve()
    print(f"   Scheduler status: {res_sched['status']}")
    assert res_sched["status"] in ("OPTIMAL", "FEASIBLE")
    weekdays_used = set(c["weekday"] for c in res_sched["classes"])
    print(f"   Weekdays allocated in 6-day mode: {sorted(weekdays_used)} (0=Mon, 5=Sat)")
    assert 5 in weekdays_used, "Saturday (5) should be scheduled in 6-day mode"
    print("   [PASS] Six-day scheduler allocates classes to Saturday (weekday 5)")

    # 5. Create Timetable Version and Test Direct PNG Download
    print("\n5. Testing PNG Timetable Generation and Download...")
    tv = db.query(TimetableVersion).filter_by(version_number=1001).first()
    if not tv:
        tv = TimetableVersion(
            academic_year_id=ay.id,
            programme_id=prog.id,
            semester_id=sem.id,
            section_id=sec.id,
            version_number=1001,
            status=VersionStatus.PUBLISHED,
            algorithm="HYBRID_CPSAT"
        )
        db.add(tv)
        db.flush()

    # Room
    room = db.query(Room).first()

    db.query(ScheduledClass).filter_by(version_id=tv.id).delete()
    for idx, c in enumerate(res_sched["classes"]):
        sc = ScheduledClass(
            version_id=tv.id,
            assignment_id=c["assignment_id"],
            subject_id=c["subject_id"],
            faculty_id=c["faculty_id"],
            room_id=room.id if room else c["room_id"],
            section_id=sec.id,
            weekday=c["weekday"],
            start_minute=c["start_minute"],
            end_minute=c["end_minute"],
            session_number=idx + 1
        )
        db.add(sc)
    db.commit()

    # Test Direct Section Download Endpoint as Admin
    dl_url = f"{BASE_BACKEND}/api/scheduling/versions/{tv.id}/section/{sec.id}/download"
    res_dl = httpx.get(dl_url, headers=admin_headers)
    assert res_dl.status_code == 200, f"PNG download failed: {res_dl.status_code}"
    assert res_dl.headers.get("Content-Type") == "image/png"
    cd = res_dl.headers.get("Content-Disposition", "")
    assert "attachment" in cd and ".png" in cd
    # Validate with PIL
    img = Image.open(io.BytesIO(res_dl.content))
    assert img.format == "PNG"
    print(f"   [PASS] PNG generated successfully: {img.size[0]}x{img.size[1]} pixels, Content-Disposition: {cd}")

    # 6. Student Portal Workflow
    print("\n6. Testing Student Portal Authentication and Restrictions...")
    student = db.query(Student).filter_by(student_id="STU-DEMO-01").first()
    if not student:
        student = Student(
            student_id="STU-DEMO-01",
            full_name="Grace Hopper",
            email="grace@student.schedulix.edu",
            admission_year=2026,
            department_id=dept.id,
            programme_id=prog.id,
            current_year=1,
            current_semester=1,
            password_hash=hash_password("Hopper@2026")
        )
        db.add(student)
        db.flush()

    enr = db.query(Enrolment).filter_by(student_id=student.id, section_id=sec.id).first()
    if not enr:
        enr = Enrolment(student_id=student.id, section_id=sec.id, active=True)
        db.add(enr)
    db.commit()

    # Login through Student Portal
    res_stu_login = httpx.post(f"{BASE_BACKEND}/api/auth/student-login", json={
        "identifier": "STU-DEMO-01",
        "password": "Hopper@2026"
    })
    assert res_stu_login.status_code == 200, f"Student login failed: {res_stu_login.text}"
    stu_token = res_stu_login.json()["access_token"]
    stu_headers = {"Authorization": f"Bearer {stu_token}"}
    print(f"   [PASS] Student login successful for {student.full_name}")

    # Profile
    res_stu_prof = httpx.get(f"{BASE_BACKEND}/api/student/profile", headers=stu_headers)
    assert res_stu_prof.status_code == 200
    prof_data = res_stu_prof.json()
    assert prof_data["student"]["student_id"] == "STU-DEMO-01"
    assert prof_data["programme"]["code"] == "BTECH-DEMO"
    assert prof_data["section"]["name"] == "A"
    print(f"   [PASS] Student profile verified: {prof_data['programme']['name']}, Sem {prof_data['student']['current_semester']}, Sec {prof_data['section']['name']}")

    # Timetable
    res_stu_tt = httpx.get(f"{BASE_BACKEND}/api/student/timetable", headers=stu_headers)
    assert res_stu_tt.status_code == 200
    tt_data = res_stu_tt.json()
    assert tt_data["status"] == "PUBLISHED"
    assert len(tt_data["classes"]) > 0
    print(f"   [PASS] Student timetable returned {len(tt_data['classes'])} classes (published version)")

    # Student PNG Download
    res_stu_png = httpx.get(f"{BASE_BACKEND}/api/student/timetable/download", headers=stu_headers)
    assert res_stu_png.status_code == 200
    assert res_stu_png.headers.get("Content-Type") == "image/png"
    img_stu = Image.open(io.BytesIO(res_stu_png.content))
    assert img_stu.format == "PNG"
    print(f"   [PASS] Student timetable PNG downloaded: {img_stu.size[0]}x{img_stu.size[1]} pixels")

    # Security: student cannot access admin routes
    res_unauth = httpx.post(f"{BASE_BACKEND}/api/academic/departments", headers=stu_headers, json={"name": "Bad", "code": "BAD"})
    assert res_unauth.status_code in (401, 403)
    print("   [PASS] Student access to admin routes is strictly forbidden (HTTP 403/401)")

    db.close()
    print("\n==================================================")
    print("ALL LIVE SYSTEM VERIFICATIONS PASSED SUCCESSFULLY!")
    print("==================================================")

if __name__ == "__main__":
    test_live_system()
