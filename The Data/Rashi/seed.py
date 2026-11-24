
import os
from datetime import date

from sqlalchemy import select

from app.database import SessionLocal
from app.models import (
    Admin,
    Department,
    Programme,
    AcademicYear,
    Semester,
    Section,
    Subject,
    Faculty,
    Student,
    Room,
    Floor,
    Building,
    Enrolment,
    RoomType,
    SessionType,
)
from app.security import hash_password


def get_or_create(db, model, lookup, defaults=None):
    """
    Return an existing database record or create it if missing.
    Prevents duplicate records when the seed script is rerun.
    """
    instance = db.scalar(
        select(model).filter_by(**lookup)
    )

    if instance is not None:
        return instance, False

    values = dict(lookup)

    if defaults:
        values.update(defaults)

    instance = model(**values)
    db.add(instance)
    db.flush()

    return instance, True


def seed():
    db = SessionLocal()

    try:
        
        # --------------------------------------------------
        # 1. ADMIN ACCOUNT
        # --------------------------------------------------

        from app.config import settings
        username = os.environ.get("ADMIN_USERNAME") or settings.ADMIN_USERNAME or "admin"
        email = os.environ.get("ADMIN_EMAIL") or settings.ADMIN_EMAIL or "admin@example.com"
        password = os.environ.get("ADMIN_PASSWORD") or settings.ADMIN_PASSWORD or "admin123456789"

        admin, admin_created = get_or_create(
            db,
            Admin,
            {"username": username},
            {
                "email": email,
                "password_hash": hash_password(password),
            },
        )

        # IMPORTANT: Update existing administrator credentials too.
        admin.email = email
        admin.password_hash = hash_password(password)
        admin.active = True

        db.flush()

        print("Administrator credentials updated successfully.")


        # --------------------------------------------------
        # 2. ACADEMIC YEAR
        # --------------------------------------------------

        year, _ = get_or_create(
            db,
            AcademicYear,
            {"name": "2026-2027"},
            {
                "start_date": date(2026, 7, 1),
                "end_date": date(2027, 6, 30),
                "active": True,
            },
        )

        # --------------------------------------------------
        # 3. DEPARTMENTS AND PROGRAMMES
        # --------------------------------------------------

        departments_data = [
            ("Computer Science and Engineering", "CSE"),
            ("Mechanical Engineering", "ME"),
            ("Civil Engineering", "CE"),
            ("Electrical Engineering", "EE"),
            ("Electronics and Communication", "ECE"),
            ("Information Technology", "IT"),
        ]

        for department_name, department_code in departments_data:

            department, _ = get_or_create(
                db,
                Department,
                {"code": department_code},
                {"name": department_name},
            )

            # --------------------------------------------------
            # 4. PROGRAMME
            # --------------------------------------------------

            programme, _ = get_or_create(
                db,
                Programme,
                {"code": f"BTECH-{department_code}"},
                {
                    "department_id": department.id,
                    "name": f"B.Tech {department_name}",
                    "duration_years": 4,
                },
            )

            # --------------------------------------------------
            # 5. SEMESTER
            # --------------------------------------------------

            semester, _ = get_or_create(
                db,
                Semester,
                {
                    "programme_id": programme.id,
                    "academic_year_id": year.id,
                    "number": 3,
                },
            )

            # --------------------------------------------------
            # 6. FACULTY
            # --------------------------------------------------

            for index in range(1, 3):

                get_or_create(
                    db,
                    Faculty,
                    {
                        "faculty_id": (
                            f"{department_code}-FAC-{index}"
                        )
                    },
                    {
                        "department_id": department.id,
                        "full_name": (
                            f"{department_code} Faculty {index}"
                        ),
                        "email": (
                            f"{department_code.lower()}."
                            f"faculty{index}@example.edu"
                        ),
                        "designation": "Assistant Professor",
                    },
                )

            # --------------------------------------------------
            # 7. SECTIONS AND STUDENTS
            # --------------------------------------------------

            for section_name in ("A", "B"):

                section, _ = get_or_create(
                    db,
                    Section,
                    {
                        "semester_id": semester.id,
                        "name": section_name,
                    },
                    {
                        "programme_id": programme.id,
                        "student_count": 40,
                    },
                )

                # Two sample students per section.

                for index in range(1, 3):

                    student, _ = get_or_create(
                        db,
                        Student,
                        {
                            "student_id": (
                                f"{department_code}-"
                                f"{section_name}-{index:03}"
                            )
                        },
                        {
                            "full_name": (
                                f"{department_code} "
                                f"{section_name} Student {index}"
                            ),
                            "email": (
                                f"{department_code.lower()}."
                                f"{section_name.lower()}."
                                f"{index}@example.edu"
                            ),
                            "admission_year": 2025,
                        },
                    )

                    # Enrolment is created only if missing.

                    get_or_create(
                        db,
                        Enrolment,
                        {
                            "student_id": student.id,
                            "section_id": section.id,
                        },
                    )

            # --------------------------------------------------
            # 8. SUBJECTS
            # --------------------------------------------------

            subjects = [
                (
                    "OS",
                    "Operating Systems",
                    SessionType.LECTURE,
                    60,
                ),
                (
                    "DBMS",
                    "Database Management Systems",
                    SessionType.LECTURE,
                    60,
                ),
                (
                    "OSLAB",
                    "Operating Systems Laboratory",
                    SessionType.LABORATORY,
                    120,
                ),
                (
                    "DBLAB",
                    "DBMS Laboratory",
                    SessionType.LABORATORY,
                    120,
                ),
            ]

            for subject_code, subject_name, kind, duration in subjects:

                get_or_create(
                    db,
                    Subject,
                    {
                        "department_id": department.id,
                        "code": subject_code,
                    },
                    {
                        "name": subject_name,
                        "session_type": kind,
                        "default_duration": duration,
                    },
                )

        # --------------------------------------------------
        # 9. SHARED CAMPUS INFRASTRUCTURE
        # --------------------------------------------------

        building, _ = get_or_create(
            db,
            Building,
            {"code": "ACA"},
            {"name": "Academic Block A"},
        )

        floor, _ = get_or_create(
            db,
            Floor,
            {
                "building_id": building.id,
                "name": "Ground Floor",
            },
            {"level": 0},
        )

        # --------------------------------------------------
        # 10. ROOMS
        # --------------------------------------------------

        rooms_list = []
        for index in range(1, 7):

            room_name = f"A-{100 + index}"

            r_inst, _ = get_or_create(
                db,
                Room,
                {
                    "floor_id": floor.id,
                    "name": room_name,
                },
                {
                    "room_type": (
                        RoomType.LABORATORY
                        if index >= 5
                        else RoomType.CLASSROOM
                    ),
                    "capacity": 50,
                    "equipment": ["Projector", "Whiteboard"],
                },
            )
            rooms_list.append(r_inst)

        # --------------------------------------------------
        # 11. CAMPUS GRAPH (NODES & EDGES)
        # --------------------------------------------------
        from app.models import CampusNode, CampusEdge, FacultyAssignment

        entrance_node, _ = get_or_create(
            db,
            CampusNode,
            {"name": "Main Academic Entrance", "node_type": "ENTRANCE"},
            {"building_id": building.id, "floor_id": floor.id}
        )

        corridor_node, _ = get_or_create(
            db,
            CampusNode,
            {"name": "Ground Floor Central Corridor", "node_type": "CORRIDOR"},
            {"building_id": building.id, "floor_id": floor.id}
        )

        get_or_create(
            db,
            CampusEdge,
            {"source_id": entrance_node.id, "target_id": corridor_node.id},
            {"distance": 20.0, "connection_type": "CORRIDOR", "bidirectional": True, "accessible": True}
        )

        room_nodes = []
        for r in rooms_list:
            r_node, _ = get_or_create(
                db,
                CampusNode,
                {"room_id": r.id},
                {"name": f"Room {r.name} Entrance", "node_type": "ROOM", "building_id": building.id, "floor_id": floor.id}
            )
            room_nodes.append(r_node)
            # Connect room node to corridor
            get_or_create(
                db,
                CampusEdge,
                {"source_id": corridor_node.id, "target_id": r_node.id},
                {"distance": 15.0 + (int(r.name.split("-")[1]) % 10) * 5, "connection_type": "WALKWAY", "bidirectional": True, "accessible": True}
            )

        # Connect adjacent rooms along corridor
        for i in range(len(room_nodes) - 1):
            get_or_create(
                db,
                CampusEdge,
                {"source_id": room_nodes[i].id, "target_id": room_nodes[i+1].id},
                {"distance": 12.0, "connection_type": "CORRIDOR", "bidirectional": True, "accessible": True}
            )

        # --------------------------------------------------
        # 12. FACULTY ASSIGNMENTS
        # --------------------------------------------------
        departments_all = db.query(Department).all()
        for dept in departments_all:
            dept_faculty = db.query(Faculty).filter(Faculty.department_id == dept.id).all()
            dept_subjects = db.query(Subject).filter(Subject.department_id == dept.id).all()
            dept_progs = db.query(Programme).filter(Programme.department_id == dept.id).all()

            for prog in dept_progs:
                prog_sections = db.query(Section).filter(Section.programme_id == prog.id).all()
                for sec in prog_sections:
                    if not dept_faculty or not dept_subjects:
                        continue
                    
                    lecture_subjects = [s for s in dept_subjects if s.session_type == SessionType.LECTURE]
                    lab_subjects = [s for s in dept_subjects if s.session_type == SessionType.LABORATORY]

                    for idx, l_sub in enumerate(lecture_subjects):
                        fac = dept_faculty[idx % len(dept_faculty)]
                        get_or_create(
                            db,
                            FacultyAssignment,
                            {
                                "faculty_id": fac.id,
                                "subject_id": l_sub.id,
                                "section_id": sec.id
                            },
                            {
                                "sessions_per_week": 3,
                                "duration_minutes": 60,
                                "priority": 7 + idx,
                                "required_capacity": 40,
                                "required_room_type": RoomType.CLASSROOM,
                                "active": True
                            }
                        )

                    for idx, lab_sub in enumerate(lab_subjects):
                        fac = dept_faculty[(idx + 1) % len(dept_faculty)]
                        get_or_create(
                            db,
                            FacultyAssignment,
                            {
                                "faculty_id": lab_fac.id if (lab_fac := dept_faculty[(idx + 1) % len(dept_faculty)]) else fac.id,
                                "subject_id": lab_sub.id,
                                "section_id": sec.id
                            },
                            {
                                "sessions_per_week": 1,
                                "duration_minutes": 120,
                                "priority": 9,
                                "required_capacity": 40,
                                "required_room_type": RoomType.LABORATORY,
                                "active": True
                            }
                        )

        # --------------------------------------------------
        # 13. COMMIT
        # --------------------------------------------------

        db.commit()

        print("\n================================")
        print("     SCHEDULIX SEED COMPLETED")
        print("================================")
        print(f"Administrator: {username}")
        print("Academic Year: 2026-2027")
        print("Departments: 6")
        print("Sections: A and B per department")
        print("Faculty: 2 per department")
        print("Sample students: 2 per section")
        print("Subjects: 4 per department")
        print("Rooms: 6")
        print("================================\n")

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    seed()
