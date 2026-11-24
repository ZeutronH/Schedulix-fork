
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    ScheduledClass, Faculty, Subject, Room, Floor, Building,
    Section, Programme, Department, Semester, AcademicYear,
    TimetableVersion
)
from app.services.academic_helper import format_section_identity


def format_minute(value):
    return f"{value // 60:02d}:{value % 60:02d}"


def get_version_classes(db: Session, version_id: str):
    return db.scalars(
        select(ScheduledClass)
        .where(ScheduledClass.version_id == version_id)
        .order_by(
            ScheduledClass.weekday,
            ScheduledClass.start_minute
        )
    ).all()


def serialise_class(db, item):
    faculty = db.get(Faculty, item.faculty_id)
    subject = db.get(Subject, item.subject_id)
    room = db.get(Room, item.room_id)
    section = db.get(Section, item.section_id)

    programme = db.get(Programme, section.programme_id) if section else None
    department = (
        db.get(Department, programme.department_id)
        if programme else None
    )
    semester = db.get(Semester, section.semester_id) if section else None
    academic_year = (
        db.get(AcademicYear, semester.academic_year_id)
        if semester else None
    )

    floor = db.get(Floor, room.floor_id) if room else None
    building = db.get(Building, floor.building_id) if floor else None

    sec_ident = format_section_identity(
        section.name if section else "",
        programme.name if programme else None,
        programme.code if programme else None,
        semester.number if semester else None
    ) if section else {"section_code": "", "section_display_name": "", "display_name": "", "full_name": ""}

    return {
        "id": item.id,
        "assignment_id": item.assignment_id,
        "faculty_id": item.faculty_id,
        "room_id": item.room_id,
        "subject_id": item.subject_id,
        "subject": subject.name if subject else "Unknown",
        "subject_code": subject.code if subject else "",
        "faculty": faculty.full_name if faculty else "Unknown",
        "faculty_code": faculty.faculty_id if faculty else "",
        "section": section.name if section else "",
        "section_id": section.id if section else "",
        "section_name": section.name if section else "",
        "section_code": sec_ident.get("section_code", ""),
        "section_display_name": sec_ident.get("section_display_name", ""),
        "display_name": sec_ident.get("display_name", ""),
        "student_count": section.student_count if section else 0,
        "programme": programme.name if programme else "",
        "programme_code": programme.code if programme else "",
        "department": department.name if department else "",
        "department_code": department.code if department else "",
        "semester": semester.number if semester else None,
        "academic_year": academic_year.name if academic_year else "",
        "room": room.name if room else "",
        "room_capacity": room.capacity if room else None,
        "building": building.name if building else "",
        "floor": floor.name if floor else "",
        "weekday": item.weekday,
        "start": format_minute(item.start_minute),
        "end": format_minute(item.end_minute),
        "start_minute": item.start_minute,
        "end_minute": item.end_minute,
        "duration": item.end_minute - item.start_minute,
        "session_type": subject.session_type.value if subject else "",
        "session_number": item.session_number
    }


def section_timetable(db, version_id, section_id):
    return [
        serialise_class(db, item)
        for item in get_version_classes(db, version_id)
        if item.section_id == section_id
    ]


def faculty_timetable(db, version_id, faculty_id):
    return [
        serialise_class(db, item)
        for item in get_version_classes(db, version_id)
        if item.faculty_id == faculty_id
    ]


def validate_timetable(db, version_id):
    classes = get_version_classes(db, version_id)
    conflicts = []
    resources = {}

    for item in classes:
        room = db.get(Room, item.room_id)
        section = db.get(Section, item.section_id)

        if not room:
            conflicts.append({
                "class_id": item.id,
                "reason": "Assigned classroom does not exist"
            })
        elif not room.available:
            conflicts.append({
                "class_id": item.id,
                "reason": f"Classroom {room.name} is unavailable"
            })

        if room and section and room.capacity < section.student_count:
            conflicts.append({
                "class_id": item.id,
                "reason": (
                    f"Room capacity {room.capacity} is below "
                    f"section strength {section.student_count}"
                )
            })

        for resource_type, resource_id in (
            ("FACULTY", item.faculty_id),
            ("ROOM", item.room_id),
            ("SECTION", item.section_id)
        ):
            key = (resource_type, resource_id, item.weekday)
            resources.setdefault(key, []).append(item)

    for key, entries in resources.items():
        entries.sort(key=lambda entry: entry.start_minute)

        for previous, current in zip(entries, entries[1:]):
            if current.start_minute < previous.end_minute:
                conflicts.append({
                    "resource": key[0],
                    "resource_id": key[1],
                    "class_a": previous.id,
                    "class_b": current.id,
                    "reason": "Overlapping assignments"
                })

    return {
        "valid": not conflicts,
        "conflicts": conflicts,
        "class_count": len(classes)
    }
