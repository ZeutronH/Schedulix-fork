"""
Rescheduling service for Schedulix.
Supports both:
1. MANUAL RESCHEDULING: Moving a session to a specific slot with real-time clash detection,
   checking faculty, room, section conflicts, room capacity, room type, and operating hours.
   Maintains timetable version history and creates a new version transactionally.
2. AUTOMATIC RESCHEDULING: Re-solving constraints with OR-Tools CP-SAT when availability shifts.
"""

from typing import Dict, Any, Optional, List
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import Session

from app.models import (
    TimetableVersion,
    ScheduledClass,
    VersionStatus,
    ReschedulingEvent,
    Faculty,
    Room,
    Section,
    Subject,
    FacultyAssignment,
    FacultyAvailability,
    AvailabilityBlock,
    AvailabilityType
)
from app.services.scheduler import HybridScheduler
from app.services.timetable import validate_timetable, format_minute
from app.audit import record_audit


class Rescheduler:
    def __init__(self, db: Session):
        self.db = db

    def check_conflicts(
        self,
        version_id: str,
        class_id: str,
        new_weekday: int,
        new_start_minute: int,
        new_end_minute: int,
        new_room_id: Optional[str] = None,
        new_faculty_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Validates whether moving a session to a target day, time, room, or faculty creates conflicts.
        Returns a list of conflict warnings (empty list if slot is conflict-free).
        """
        conflicts = []

        target_class = self.db.get(ScheduledClass, class_id)
        if not target_class:
            return {"valid": False, "conflicts": ["Target scheduled class not found"]}

        faculty_id = new_faculty_id or target_class.faculty_id
        room_id = new_room_id or target_class.room_id
        section_id = target_class.section_id

        # 1. Operating hours validation
        if new_start_minute < 480 or new_end_minute > 1200 or new_end_minute <= new_start_minute:
            conflicts.append(
                f"Time window ({format_minute(new_start_minute)} - {format_minute(new_end_minute)}) is outside university operating hours (08:00 - 20:00)."
            )

        # 2. Weekday validation
        if new_weekday not in range(7):
            conflicts.append("Invalid weekday selected.")

        # 3. Faculty clash check in the same timetable version
        faculty = self.db.get(Faculty, faculty_id)
        fac_clashes = self.db.scalars(
            select(ScheduledClass).where(
                ScheduledClass.version_id == version_id,
                ScheduledClass.id != class_id,
                ScheduledClass.faculty_id == faculty_id,
                ScheduledClass.weekday == new_weekday,
                ScheduledClass.start_minute < new_end_minute,
                ScheduledClass.end_minute > new_start_minute
            )
        ).all()

        if fac_clashes:
            c = fac_clashes[0]
            subj = self.db.get(Subject, c.subject_id)
            conflicts.append(
                f"Faculty Clash: {faculty.full_name if faculty else 'Faculty'} is already scheduled for '{subj.name if subj else 'Class'}' at {format_minute(c.start_minute)} - {format_minute(c.end_minute)} on {c.weekday}."
            )

        # 4. Room clash check
        room = self.db.get(Room, room_id)
        if room:
            # Check capacity and type
            assignment = self.db.get(FacultyAssignment, target_class.assignment_id)
            section = self.db.get(Section, section_id)
            student_count = section.student_count if section else 0
            if room.capacity < student_count:
                conflicts.append(
                    f"Room Capacity Clash: {room.name} capacity ({room.capacity}) is smaller than section student count ({student_count})."
                )

            if assignment and assignment.required_room_type.value != room.room_type.value:
                conflicts.append(
                    f"Room Type Mismatch: Assignment requires {assignment.required_room_type.value}, but {room.name} is a {room.room_type.value}."
                )

            room_clashes = self.db.scalars(
                select(ScheduledClass).where(
                    ScheduledClass.version_id == version_id,
                    ScheduledClass.id != class_id,
                    ScheduledClass.room_id == room_id,
                    ScheduledClass.weekday == new_weekday,
                    ScheduledClass.start_minute < new_end_minute,
                    ScheduledClass.end_minute > new_start_minute
                )
            ).all()

            if room_clashes:
                c = room_clashes[0]
                subj = self.db.get(Subject, c.subject_id)
                conflicts.append(
                    f"Room Clash: {room.name} is already occupied by '{subj.name if subj else 'Class'}' at {format_minute(c.start_minute)} - {format_minute(c.end_minute)}."
                )

        # 5. Section clash check
        section_clashes = self.db.scalars(
            select(ScheduledClass).where(
                ScheduledClass.version_id == version_id,
                ScheduledClass.id != class_id,
                ScheduledClass.section_id == section_id,
                ScheduledClass.weekday == new_weekday,
                ScheduledClass.start_minute < new_end_minute,
                ScheduledClass.end_minute > new_start_minute
            )
        ).all()

        if section_clashes:
            c = section_clashes[0]
            subj = self.db.get(Subject, c.subject_id)
            conflicts.append(
                f"Section Clash: Section already has '{subj.name if subj else 'Class'}' at {format_minute(c.start_minute)} - {format_minute(c.end_minute)}."
            )

        return {
            "valid": len(conflicts) == 0,
            "conflicts": conflicts
        }

    def manual_reschedule(
        self,
        version_id: str,
        class_id: str,
        new_weekday: int,
        new_start_minute: int,
        new_end_minute: int,
        new_room_id: Optional[str] = None,
        new_faculty_id: Optional[str] = None,
        reason: str = "Manual administrative adjustment",
        admin_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes manual rescheduling in a safe ACID transaction:
        1. Checks conflicts. If invalid, aborts and returns meaningful errors.
        2. Creates a new TimetableVersion to maintain history.
        3. Clones existing scheduled classes, updating the rescheduled session.
        4. Logs ReschedulingEvent and AuditLog.
        """
        # Validate conflicts first
        check = self.check_conflicts(
            version_id=version_id,
            class_id=class_id,
            new_weekday=new_weekday,
            new_start_minute=new_start_minute,
            new_end_minute=new_end_minute,
            new_room_id=new_room_id,
            new_faculty_id=new_faculty_id
        )

        if not check["valid"]:
            raise ValueError("; ".join(check["conflicts"]))

        old_version = self.db.get(TimetableVersion, version_id)
        if not old_version:
            raise ValueError("Timetable version not found")

        # Create new version to preserve history
        latest_version = self.db.scalar(
            select(TimetableVersion.version_number)
            .order_by(TimetableVersion.version_number.desc())
            .limit(1)
        ) or old_version.version_number

        new_version = TimetableVersion(
            version_number=latest_version + 1,
            status=VersionStatus.DRAFT,
            algorithm=f"{old_version.algorithm}_MANUAL",
            priority_weight=old_version.priority_weight,
            sjf_weight=old_version.sjf_weight,
            quality_score=old_version.quality_score,
            created_by=admin_id,
            statistics={
                **old_version.statistics,
                "rescheduled_from": version_id,
                "rescheduled_class_id": class_id,
                "reason": reason
            }
        )
        self.db.add(new_version)
        self.db.flush()

        # Clone all scheduled classes into new version, with the target class modified
        old_classes = self.db.scalars(
            select(ScheduledClass).where(ScheduledClass.version_id == version_id)
        ).all()

        modified_new_id = None
        for c in old_classes:
            if c.id == class_id:
                new_class = ScheduledClass(
                    version_id=new_version.id,
                    assignment_id=c.assignment_id,
                    faculty_id=new_faculty_id or c.faculty_id,
                    section_id=c.section_id,
                    subject_id=c.subject_id,
                    room_id=new_room_id or c.room_id,
                    weekday=new_weekday,
                    start_minute=new_start_minute,
                    end_minute=new_end_minute,
                    session_number=c.session_number,
                    manual_override=True
                )
            else:
                new_class = ScheduledClass(
                    version_id=new_version.id,
                    assignment_id=c.assignment_id,
                    faculty_id=c.faculty_id,
                    section_id=c.section_id,
                    subject_id=c.subject_id,
                    room_id=c.room_id,
                    weekday=c.weekday,
                    start_minute=c.start_minute,
                    end_minute=c.end_minute,
                    session_number=c.session_number,
                    manual_override=c.manual_override
                )
            self.db.add(new_class)
            self.db.flush()
            if c.id == class_id:
                modified_new_id = new_class.id

        # Record Rescheduling Event
        event = ReschedulingEvent(
            old_version_id=version_id,
            new_version_id=new_version.id,
            reason=reason,
            affected_classes=[class_id],
            status="APPLIED"
        )
        self.db.add(event)

        record_audit(
            self.db,
            "MANUAL_RESCHEDULING",
            "ScheduledClass",
            class_id,
            admin_id,
            {
                "old_version_id": version_id,
                "new_version_id": new_version.id,
                "new_weekday": new_weekday,
                "new_start_minute": new_start_minute,
                "new_end_minute": new_end_minute,
                "reason": reason
            }
        )

        self.db.commit()

        return {
            "status": "RESCHEDULED",
            "event_id": event.id,
            "old_version_id": version_id,
            "new_version_id": new_version.id,
            "new_version_number": new_version.version_number,
            "modified_class_id": modified_new_id,
            "validation": validate_timetable(self.db, new_version.id)
        }

    def create_proposal(self, old_version_id, reason, admin_id=None):
        """Automatic re-solving proposal via OR-Tools CP-SAT."""
        old = self.db.execute(
            select(TimetableVersion)
            .where(TimetableVersion.id == old_version_id)
            .with_for_update()
        ).scalar_one_or_none()

        if not old:
            raise ValueError("Original timetable not found")

        if old.status != VersionStatus.PUBLISHED:
            raise ValueError("Only a published timetable can be rescheduled automatically.")

        if not reason or not reason.strip():
            raise ValueError("A rescheduling reason is required")

        settings_dict = old.statistics.get("scheduling_settings", {})

        scheduler = HybridScheduler(
            self.db,
            mode=old.algorithm,
            priority_weight=old.priority_weight,
            sjf_weight=old.sjf_weight,
            weekdays=settings_dict.get("weekdays", [0, 1, 2, 3, 4]),
            day_start=settings_dict.get("day_start", 480),
            day_end=settings_dict.get("day_end", 1080),
            time_limit=settings_dict.get("time_limit_seconds", 30)
        )

        result = scheduler.solve()

        if result["status"] not in ("OPTIMAL", "FEASIBLE"):
            raise ValueError({
                "message": "Automatic rescheduling failed. Original timetable remains published.",
                "solver": result["status"],
                "unscheduled": result["unscheduled"],
                "statistics": result["statistics"]
            })

        latest = self.db.scalar(
            select(TimetableVersion.version_number)
            .order_by(TimetableVersion.version_number.desc())
            .limit(1)
        ) or old.version_number

        new_version = TimetableVersion(
            version_number=latest + 1,
            status=VersionStatus.DRAFT,
            algorithm=old.algorithm,
            priority_weight=old.priority_weight,
            sjf_weight=old.sjf_weight,
            quality_score=result["quality_score"],
            created_by=admin_id,
            statistics={
                **result["statistics"],
                "unscheduled": result["unscheduled"],
                "scheduling_settings": settings_dict,
                "rescheduled_from": old_version_id,
                "rescheduling_reason": reason.strip()
            }
        )

        self.db.add(new_version)
        self.db.flush()

        for item in result["classes"]:
            self.db.add(ScheduledClass(
                version_id=new_version.id,
                assignment_id=item["assignment_id"],
                faculty_id=item["faculty_id"],
                section_id=item["section_id"],
                subject_id=item["subject_id"],
                room_id=item["room_id"],
                weekday=item["weekday"],
                start_minute=item["start_minute"],
                end_minute=item["end_minute"],
                session_number=item["session_number"]
            ))

        self.db.flush()

        validation = validate_timetable(self.db, new_version.id)

        old_classes = self.db.scalars(
            select(ScheduledClass).where(
                ScheduledClass.version_id == old_version_id
            )
        ).all()

        event = ReschedulingEvent(
            old_version_id=old_version_id,
            new_version_id=new_version.id,
            reason=reason.strip(),
            affected_classes=[item.id for item in old_classes],
            status=(
                "PROPOSED"
                if validation["valid"] and not result["unscheduled"]
                else "NEEDS_REVIEW"
            )
        )

        self.db.add(event)
        self.db.commit()

        return {
            "version_id": new_version.id,
            "version_number": new_version.version_number,
            "event_id": event.id,
            "solver": result["status"],
            "quality_score": result["quality_score"],
            "validation": validation,
            "unscheduled": result["unscheduled"],
            "status": event.status
        }
