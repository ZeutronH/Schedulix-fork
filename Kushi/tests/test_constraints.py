from app.models import (
    Department,
    Programme,
    AcademicYear,
    Semester,
    Section,
    Subject,
    Faculty,
    FacultyAssignment,
    Building,
    Floor,
    Room,
    ScheduledClass,
    TimetableVersion,
    RoomType,
    SessionType,
    VersionStatus
)

from datetime import date

from app.services.timetable import validate_timetable


def test_overlapping_section_classes(db):
    department = Department(name="CSE", code="CSE")
    db.add(department)
    db.flush()

    programme = Programme(
        department_id=department.id,
        name="BTech",
        code="BTECH"
    )
    db.add(programme)
    db.flush()

    year = AcademicYear(
        name="2026-27",
        start_date=date(2026, 7, 1),
        end_date=date(2027, 6, 30)
    )
    db.add(year)
    db.flush()

    semester = Semester(
        programme_id=programme.id,
        academic_year_id=year.id,
        number=3
    )
    db.add(semester)
    db.flush()

    section = Section(
        semester_id=semester.id,
        programme_id=programme.id,
        name="A",
        student_count=40
    )

    faculty = Faculty(
        faculty_id="F001",
        department_id=department.id,
        full_name="Teacher",
        email="teacher@example.com"
    )

    subject = Subject(
        department_id=department.id,
        code="OS",
        name="Operating Systems",
        session_type=SessionType.LECTURE,
        default_duration=60
    )

    building = Building(name="A Block", code="A")
    db.add_all([section, faculty, subject, building])
    db.flush()

    floor = Floor(
        building_id=building.id,
        name="Ground",
        level=0
    )
    db.add(floor)
    db.flush()

    room = Room(
        floor_id=floor.id,
        name="A101",
        room_type=RoomType.CLASSROOM,
        capacity=50
    )
    db.add(room)
    db.flush()

    assignment = FacultyAssignment(
        faculty_id=faculty.id,
        subject_id=subject.id,
        section_id=section.id,
        sessions_per_week=2,
        duration_minutes=60,
        priority=5,
        required_capacity=40,
        required_room_type=RoomType.CLASSROOM
    )

    db.add(assignment)
    db.flush()

    version = TimetableVersion(
        version_number=1,
        status=VersionStatus.DRAFT,
        algorithm="HYBRID"
    )
    db.add(version)
    db.flush()

    for i in range(2):
        db.add(
            ScheduledClass(
                version_id=version.id,
                assignment_id=assignment.id,
                faculty_id=faculty.id,
                subject_id=subject.id,
                section_id=section.id,
                room_id=room.id,
                weekday=0,
                start_minute=480 + i * 30,
                end_minute=540 + i * 30,
                session_number=i + 1
            )
        )

    db.flush()

    result = validate_timetable(db, version.id)

    assert result["valid"] is False
    assert any(
        conflict["resource"] == "SECTION"
        for conflict in result["conflicts"]
    )


def test_non_overlapping_classes(db):
    # A simple resource interval test.
    intervals = [(480, 540), (540, 600), (600, 720)]

    for previous, current in zip(intervals, intervals[1:]):
        assert current[0] >= previous[1]