
from collections import defaultdict
from dataclasses import dataclass
from time import monotonic

from ortools.sat.python import cp_model
from sqlalchemy import select

from app.models import (
    FacultyAssignment, Faculty, Subject, Section, Room, Floor, Building,
    AvailabilityBlock, AvailabilityType, FacultyAvailability
)


@dataclass
class Job:
    assignment_id: str
    faculty_id: str
    subject_id: str
    section_id: str
    duration: int
    priority: int
    capacity: int
    room_type: str
    subject_name: str
    faculty_name: str
    session_type: str
    session_number: int = 1
    sessions: int = 1


class HybridScheduler:
    def __init__(
        self, db, mode="HYBRID", priority_weight=0.65,
        sjf_weight=0.35, weekdays=None, day_start=480,
        day_end=1080, time_limit=30,
        section_id=None, semester_id=None, programme_id=None, academic_year_id=None
    ):
        self.db = db
        self.mode = mode.upper()
        self.priority_weight = priority_weight
        self.sjf_weight = sjf_weight
        self.weekdays = sorted(set(
            weekdays if weekdays is not None else [0, 1, 2, 3, 4, 5]
        ))
        self.day_start = day_start
        self.day_end = day_end
        self.time_limit = time_limit
        self.section_id = section_id
        self.semester_id = semester_id
        self.programme_id = programme_id
        self.academic_year_id = academic_year_id

        if self.mode not in {"HYBRID", "PRIORITY", "SJF"}:
            raise ValueError("Mode must be HYBRID, PRIORITY or SJF")
        if abs(priority_weight + sjf_weight - 1) > 1e-6:
            raise ValueError("Scheduling weights must sum to 1")
        if not self.weekdays or any(d not in range(7) for d in self.weekdays):
            raise ValueError("Select at least one valid weekday")
        if day_end <= day_start:
            raise ValueError("End time must be after start time")

    @staticmethod
    def minute(value):
        return value.hour * 60 + value.minute

    def load_jobs(self):
        query = select(FacultyAssignment).where(
            FacultyAssignment.active.is_(True)
        )
        if self.section_id:
            query = query.where(FacultyAssignment.section_id == self.section_id)
        elif self.semester_id:
            query = query.join(Section, Section.id == FacultyAssignment.section_id).where(
                Section.semester_id == self.semester_id
            )
        elif self.programme_id:
            query = query.join(Section, Section.id == FacultyAssignment.section_id).where(
                Section.programme_id == self.programme_id
            )

        assignments = self.db.scalars(query).all()

        jobs = []
        problems = []

        for assignment in assignments:
            faculty = self.db.get(Faculty, assignment.faculty_id)
            subject = self.db.get(Subject, assignment.subject_id)
            section = self.db.get(Section, assignment.section_id)

            if not faculty or not subject or not section:
                problems.append({
                    "assignment_id": assignment.id,
                    "reason": "Faculty, subject or section record is missing"
                })
                continue

            if not faculty.active:
                problems.append({
                    "assignment_id": assignment.id,
                    "reason": "Assigned faculty member is inactive"
                })
                continue

            for session_no in range(1, assignment.sessions_per_week + 1):
                jobs.append(Job(
                    assignment_id=assignment.id,
                    faculty_id=faculty.id,
                    subject_id=subject.id,
                    section_id=section.id,
                    duration=assignment.duration_minutes,
                    priority=assignment.priority,
                    capacity=max(
                        assignment.required_capacity or 0,
                        section.student_count
                    ),
                    room_type=assignment.required_room_type.value,
                    subject_name=subject.name,
                    faculty_name=faculty.full_name,
                    session_type=subject.session_type.value,
                    session_number=session_no
                ))

        return jobs, problems

    def load_rooms(self):
        floors = {f.id: f for f in self.db.scalars(select(Floor)).all()}
        buildings = {b.id: b for b in self.db.scalars(select(Building)).all()}

        rooms = self.db.scalars(
            select(Room).where(Room.available.is_(True))
        ).all()

        result = []
        for room in rooms:
            floor = floors.get(room.floor_id)
            if not floor:
                continue
            building = buildings.get(floor.building_id)
            if building and building.available:
                result.append(room)
        return result

    def blocked(self, resource_type, resource_id, day, start, end):
        if hasattr(self, "_cached_blocks"):
            for b_day, b_start, b_end in self._cached_blocks.get((resource_type, resource_id), []):
                if b_day == day and start < b_end and b_start < end:
                    return True
            return False

        blocks = self.db.scalars(
            select(AvailabilityBlock).where(
                AvailabilityBlock.resource_type == resource_type,
                AvailabilityBlock.resource_id == resource_id
            )
        ).all()

        for block in blocks:
            if block.start_at.weekday() != day:
                continue
            block_start = self.minute(block.start_at.time())
            block_end = self.minute(block.end_at.time())
            if start < block_end and block_start < end:
                return True
        return False

    def teacher_available(self, faculty_id, day, start, end):
        if hasattr(self, "_cached_faculty_avail"):
            records = self._cached_faculty_avail.get((faculty_id, day))
            if not records:
                return True
            return any(
                avail and s_time <= start and e_time >= end
                for avail, s_time, e_time in records
            )

        records = self.db.scalars(
            select(FacultyAvailability).where(
                FacultyAvailability.faculty_id == faculty_id,
                FacultyAvailability.weekday == day
            )
        ).all()

        if not records:
            return True

        return any(
            record.available
            and self.minute(record.start_time) <= start
            and self.minute(record.end_time) >= end
            for record in records
        )

    def room_suitable(self, job, room):
        return (
            room.available
            and room.capacity >= job.capacity
            and room.room_type.value == job.room_type
        )

    def score(self, job, min_duration, max_duration):
        priority = job.priority / 10
        sjf = (
            1.0 if max_duration == min_duration
            else (max_duration - job.duration) /
                 (max_duration - min_duration)
        )

        if self.mode == "PRIORITY":
            return priority
        if self.mode == "SJF":
            return sjf
        return (
            self.priority_weight * priority
            + self.sjf_weight * sjf
        )

    get_score = score

    def load_external_commitments(self):
        """
        Loads scheduled classes from PUBLISHED or APPROVED versions of OTHER sections.
        Treats their (faculty_id, weekday, start, end) and (room_id, weekday, start, end)
        as busy intervals so shared faculty and shared classrooms are never double-booked.
        """
        from app.models import ScheduledClass, TimetableVersion, VersionStatus
        if not self.section_id:
            return defaultdict(list), defaultdict(list)

        # For other sections, find the latest active published or approved version
        versions = self.db.scalars(
            select(TimetableVersion)
            .where(TimetableVersion.status.in_([VersionStatus.PUBLISHED, VersionStatus.APPROVED]))
            .order_by(TimetableVersion.version_number.desc())
        ).all()

        section_latest_version = {}
        for v in versions:
            secs = self.db.scalars(
                select(ScheduledClass.section_id)
                .where(ScheduledClass.version_id == v.id)
                .distinct()
            ).all()
            for s_id in secs:
                if s_id != self.section_id and s_id not in section_latest_version:
                    section_latest_version[s_id] = v.id

        active_v_ids = set(section_latest_version.values())
        if not active_v_ids:
            return defaultdict(list), defaultdict(list)

        other_classes = self.db.scalars(
            select(ScheduledClass)
            .where(
                ScheduledClass.section_id != self.section_id,
                ScheduledClass.version_id.in_(active_v_ids)
            )
        ).all()
        busy_faculty = defaultdict(list)
        busy_rooms = defaultdict(list)

        for sc in other_classes:
            busy_faculty[(sc.faculty_id, sc.weekday)].append((sc.start_minute, sc.end_minute))
            busy_rooms[(sc.room_id, sc.weekday)].append((sc.start_minute, sc.end_minute))

        return busy_faculty, busy_rooms

    def solve(self):
        started = monotonic()
        jobs, data_problems = self.load_jobs()
        rooms = self.load_rooms()
        busy_faculty, busy_rooms = self.load_external_commitments()

        if not jobs:
            return {
                "status": "EMPTY",
                "classes": [],
                "unscheduled": data_problems or [{
                    "reason": "No active faculty assignments found. Create faculty-subject-section assignments first."
                }],
                "quality_score": 0,
                "statistics": {
                    "total_jobs": 0,
                    "scheduled": 0,
                    "unscheduled": 0,
                    "active_rooms": len(rooms),
                    "solver_status": "EMPTY"
                }
            }

        if not rooms:
            return {
                "status": "INFEASIBLE",
                "classes": [],
                "unscheduled": [
                    {
                        "assignment_id": job.assignment_id,
                        "session_number": job.session_number,
                        "reason": "No available classrooms exist"
                    }
                    for job in jobs
                ],
                "quality_score": 0,
                "statistics": {
                    "total_jobs": len(jobs),
                    "scheduled": 0,
                    "unscheduled": len(jobs),
                    "active_rooms": 0,
                    "solver_status": "INFEASIBLE"
                }
            }

        model = cp_model.CpModel()
        candidates = []
        by_job = defaultdict(list)
        by_resource = defaultdict(list)
        no_candidate_reasons = {}

        # Pre-cache availability blocks: (resource_type, resource_id) -> list of (weekday, start_min, end_min)
        all_blocks = self.db.scalars(select(AvailabilityBlock)).all()
        self._cached_blocks = defaultdict(list)
        for b in all_blocks:
            self._cached_blocks[(b.resource_type, b.resource_id)].append((
                b.start_at.weekday(),
                self.minute(b.start_at.time()),
                self.minute(b.end_at.time())
            ))

        # Pre-cache faculty availability: (faculty_id, weekday) -> list of (available, start_min, end_min)
        all_faculty_avail = self.db.scalars(select(FacultyAvailability)).all()
        self._cached_faculty_avail = defaultdict(list)
        for fa in all_faculty_avail:
            self._cached_faculty_avail[(fa.faculty_id, fa.weekday)].append((
                fa.available,
                self.minute(fa.start_time),
                self.minute(fa.end_time)
            ))

        # Pre-cache floor and building hierarchy for rooms
        floors = {f.id: f for f in self.db.scalars(select(Floor)).all()}
        room_checks = {}
        for room in rooms:
            floor = floors.get(room.floor_id)
            if floor:
                room_checks[room.id] = [
                    (AvailabilityType.ROOM, room.id),
                    (AvailabilityType.FLOOR, floor.id),
                    (AvailabilityType.BUILDING, floor.building_id)
                ]
            else:
                room_checks[room.id] = [(AvailabilityType.ROOM, room.id)]

        min_duration = min(job.duration for job in jobs)
        max_duration = max(job.duration for job in jobs)

        for job_index, job in enumerate(jobs):
            suitable_rooms = [
                room for room in rooms
                if self.room_suitable(job, room)
            ]

            if not suitable_rooms:
                no_candidate_reasons[job_index] = (
                    "No classroom has the required room type and capacity"
                )
                continue

            time_step = 60 if min_duration >= 60 else 30
            for day in self.weekdays:
                for start in range(
                    self.day_start,
                    self.day_end - job.duration + 1,
                    time_step
                ):
                    end = start + job.duration

                    if not self.teacher_available(
                        job.faculty_id, day, start, end
                    ):
                        continue

                    if self.blocked(
                        AvailabilityType.FACULTY,
                        job.faculty_id, day, start, end
                    ):
                        continue

                    # Check external commitments from other sections (shared faculty)
                    if any(s < end and start < e for s, e in busy_faculty.get((job.faculty_id, day), [])):
                        continue

                    for room in suitable_rooms:
                        checks = room_checks.get(room.id, [])
                        if any(
                            self.blocked(kind, resource_id, day, start, end)
                            for kind, resource_id in checks
                        ):
                            continue

                        # Check external commitments from other sections (shared classroom)
                        if any(s < end and start < e for s, e in busy_rooms.get((room.id, day), [])):
                            continue

                        variable = model.new_bool_var(
                            f"j{job_index}_d{day}_t{start}_r{room.id}"
                        )

                        candidate = {
                            "var": variable,
                            "job": job_index,
                            "day": day,
                            "start": start,
                            "end": end,
                            "room": room.id
                        }

                        candidates.append(candidate)
                        by_job[job_index].append(candidate)

                        # Track candidate active time intervals for O(N) linear resource conflict enforcement
                        step_res = 30
                        for t in range(start, end, step_res):
                            by_resource[("FACULTY", job.faculty_id, day, t)].append(variable)
                            by_resource[("SECTION", job.section_id, day, t)].append(variable)
                            by_resource[("ROOM", room.id, day, t)].append(variable)

            if not by_job[job_index]:
                no_candidate_reasons.setdefault(
                    job_index,
                    "No placement fits the working hours and availability constraints"
                )

        # Faculty cache for workload safety limits
        unique_faculty_ids = set(job.faculty_id for job in jobs)
        faculties = self.db.scalars(
            select(Faculty).where(Faculty.id.in_(unique_faculty_ids))
        ).all() if unique_faculty_ids else []
        faculty_cache = {fac.id: fac for fac in faculties}

        # Group candidates by faculty-day, faculty-week, section-day
        by_faculty_day = defaultdict(list)
        by_faculty_week = defaultdict(list)
        by_section_day = defaultdict(list)

        for candidate in candidates:
            job = jobs[candidate["job"]]
            by_faculty_day[(job.faculty_id, candidate["day"])].append(candidate["var"])
            by_faculty_week[job.faculty_id].append(candidate["var"])
            by_section_day[(job.section_id, candidate["day"])].append(candidate["var"])

        # Each job is scheduled at most once. This allows a useful
        # partial timetable to be returned when some jobs are impossible.
        for job_index, options in by_job.items():
            model.add(sum(option["var"] for option in options) <= 1)

        # Prevent overlapping use of faculty, rooms and sections via linear time-point constraints
        for resource_key, var_list in by_resource.items():
            if len(var_list) > 1:
                model.add(sum(var_list) <= 1)

        # HARD CONSTRAINT: Faculty Daily Workload Limit (max_classes_per_day)
        # Accounts for external commitments from other section timetables
        for (fac_id, day), var_list in by_faculty_day.items():
            fac = faculty_cache.get(fac_id)
            max_daily = fac.max_classes_per_day if fac and fac.max_classes_per_day else 4
            existing_daily = len(busy_faculty.get((fac_id, day), []))
            remaining_daily = max(0, max_daily - existing_daily)
            model.add(sum(var_list) <= remaining_daily)

        # HARD CONSTRAINT: Faculty Weekly Workload Limit (max_classes_per_week)
        # Accounts for external commitments from other section timetables
        for fac_id, var_list in by_faculty_week.items():
            fac = faculty_cache.get(fac_id)
            max_weekly = fac.max_classes_per_week if fac and fac.max_classes_per_week else 18
            existing_weekly = sum(len(slots) for (fid, d), slots in busy_faculty.items() if fid == fac_id)
            remaining_weekly = max(0, max_weekly - existing_weekly)
            model.add(sum(var_list) <= remaining_weekly)

        # HARD CONSTRAINT: Maximum Consecutive Classes & Break Protection
        # In any window of (max_consecutive_hours + 1) slots (60m step),
        # faculty cannot be scheduled in all of them without a break.
        for fac_id, fac in faculty_cache.items():
            max_consec = fac.max_consecutive_hours if fac and fac.max_consecutive_hours else 2
            if max_consec > 0:
                for day in self.weekdays:
                    # Check sliding window of max_consec + 1 hours
                    window_hours = max_consec + 1
                    for win_start in range(self.day_start, self.day_end - window_hours * 60 + 1, 60):
                        consec_vars = []
                        for h in range(window_hours):
                            slot_time = win_start + h * 60
                            consec_vars.extend(by_resource.get(("FACULTY", fac_id, day, slot_time), []))
                        if len(consec_vars) > max_consec:
                            # Cannot exceed max_consec in this consecutive window
                            model.add(sum(consec_vars) <= max_consec)

        # HARD CONSTRAINT: Section Daily Balance
        # Prevent piling all classes into 1-2 days when multiple days are configured.
        # Spreads load across Monday through Saturday when 6 days are configured.
        unique_section_ids = set(job.section_id for job in jobs)
        for sec_id in unique_section_ids:
            total_sec_jobs = sum(1 for j in jobs if j.section_id == sec_id)
            num_days = len(self.weekdays)
            max_sec_per_day = max(3, (total_sec_jobs + num_days - 1) // num_days + 2)
            for day in self.weekdays:
                sec_day_vars = by_section_day.get((sec_id, day), [])
                if sec_day_vars and len(sec_day_vars) > max_sec_per_day:
                    model.add(sum(sec_day_vars) <= max_sec_per_day)

        # Prioritise scheduling every possible class first.
        # Then optimise Priority/SJF quality and balanced day distribution.
        objective = []
        for candidate in candidates:
            job = jobs[candidate["job"]]
            score_units = int(
                self.score(job, min_duration, max_duration) * 10000
            )
            tie_breaker = candidate["start"] - self.day_start
            objective.append(
                candidate["var"] * (1_000_000_000 + score_units * 1000 - tie_breaker)
            )

        # SOFT OBJECTIVE: Workload Balancing & Saturday Allocation
        # Reward utilizing each configured weekday (including Saturday) so sessions
        # don't clump unnecessarily and Saturday gets scheduled when 6 days are configured.
        for sec_id in unique_section_ids:
            for day in self.weekdays:
                sec_day_vars = by_section_day.get((sec_id, day), [])
                if sec_day_vars:
                    day_active_var = model.new_bool_var(f"active_sec_{sec_id}_d{day}")
                    for v in sec_day_vars:
                        model.add(day_active_var >= v)
                    model.add(day_active_var <= sum(sec_day_vars))
                    bonus = 60_000 if day == 5 else 50_000
                    objective.append(day_active_var * bonus)

        model.maximize(sum(objective))

        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = self.time_limit
        solver.parameters.num_search_workers = 8
        status = solver.solve(model)
        status_name = solver.status_name(status)

        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            unscheduled = []
            for index, job in enumerate(jobs):
                unscheduled.append({
                    "assignment_id": job.assignment_id,
                    "session_number": job.session_number,
                    "subject": job.subject_name,
                    "section_id": job.section_id,
                    "reason": no_candidate_reasons.get(
                        index, "Solver could not find a feasible solution"
                    )
                })

            return {
                "status": status_name,
                "classes": [],
                "unscheduled": unscheduled,
                "quality_score": 0,
                "statistics": {
                    "total_jobs": len(jobs),
                    "scheduled": 0,
                    "unscheduled": len(jobs),
                    "candidate_count": len(candidates),
                    "solver_status": status_name,
                    "elapsed_seconds": round(monotonic() - started, 3)
                }
            }

        output = []
        unscheduled = []
        selected_indices = set()

        for job_index, job in enumerate(jobs):
            selected = next(
                (
                    candidate for candidate in by_job[job_index]
                    if solver.value(candidate["var"]) == 1
                ),
                None
            )

            if selected is None:
                unscheduled.append({
                    "assignment_id": job.assignment_id,
                    "session_number": job.session_number,
                    "subject": job.subject_name,
                    "section_id": job.section_id,
                    "reason": no_candidate_reasons.get(
                        job_index, "No conflict-free placement was selected"
                    )
                })
                continue

            selected_indices.add(job_index)
            output.append({
                "assignment_id": job.assignment_id,
                "faculty_id": job.faculty_id,
                "subject_id": job.subject_id,
                "section_id": job.section_id,
                "room_id": selected["room"],
                "weekday": selected["day"],
                "start_minute": selected["start"],
                "end_minute": selected["end"],
                "duration": job.duration,
                "priority": job.priority,
                "subject": job.subject_name,
                "faculty": job.faculty_name,
                "session_type": job.session_type,
                "session_number": job.session_number
            })

        total_score = sum(
            self.score(job, min_duration, max_duration)
            for job in jobs
        )
        achieved_score = sum(
            self.score(jobs[index], min_duration, max_duration)
            for index in selected_indices
        )

        quality = (
            100 * achieved_score / total_score
            if total_score else 0
        )

        return {
            "status": status_name,
            "classes": output,
            "unscheduled": unscheduled,
            "quality_score": round(quality, 2),
            "statistics": {
                "total_jobs": len(jobs),
                "scheduled": len(output),
                "unscheduled": len(unscheduled),
                "active_rooms": len(rooms),
                "candidate_count": len(candidates),
                "solver_status": status_name,
                "elapsed_seconds": round(monotonic() - started, 3)
            }
        }
