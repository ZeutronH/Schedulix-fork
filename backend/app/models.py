import enum
import uuid

from datetime import datetime, time

from sqlalchemy import (
    String, Integer, Boolean, DateTime, Date, Time,
    Float, ForeignKey, Text, Enum, UniqueConstraint,
    CheckConstraint, Index, JSON, BigInteger
)

from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def new_id():
    return str(uuid.uuid4())


class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"


class SessionType(str, enum.Enum):
    LECTURE = "LECTURE"
    LABORATORY = "LABORATORY"
    TUTORIAL = "TUTORIAL"
    PRACTICAL = "PRACTICAL"


class RoomType(str, enum.Enum):
    CLASSROOM = "CLASSROOM"
    LABORATORY = "LABORATORY"
    SEMINAR = "SEMINAR"
    AUDITORIUM = "AUDITORIUM"


class VersionStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    PUBLISHED = "PUBLISHED"
    SUPERSEDED = "SUPERSEDED"


class AvailabilityType(str, enum.Enum):
    FACULTY = "FACULTY"
    ROOM = "ROOM"
    BUILDING = "BUILDING"
    FLOOR = "FLOOR"


class DeliveryStatus(str, enum.Enum):
    QUEUED = "QUEUED"
    SENT = "SENT"
    DELIVERED = "DELIVERED"
    READ = "READ"
    FAILED = "FAILED"


class Admin(Base):
    __tablename__ = "admins"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    username: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(150), unique=True)
    code: Mapped[str] = mapped_column(String(20), unique=True)
    description: Mapped[str | None] = mapped_column(Text)

    programmes = relationship("Programme", back_populates="department")
    faculty = relationship("Faculty", back_populates="department")


class Programme(Base):
    __tablename__ = "programmes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    department_id: Mapped[str] = mapped_column(ForeignKey("departments.id"))
    name: Mapped[str] = mapped_column(String(150))
    code: Mapped[str] = mapped_column(String(30))
    duration_years: Mapped[int] = mapped_column(Integer, default=4)

    department = relationship("Department", back_populates="programmes")
    sections = relationship("Section", back_populates="programme")

    __table_args__ = (
        UniqueConstraint("department_id", "code"),
    )


class AcademicYear(Base):
    __tablename__ = "academic_years"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(30), unique=True)
    start_date: Mapped[datetime] = mapped_column(Date)
    end_date: Mapped[datetime] = mapped_column(Date)
    active: Mapped[bool] = mapped_column(Boolean, default=False)


class Semester(Base):
    __tablename__ = "semesters"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    programme_id: Mapped[str] = mapped_column(ForeignKey("programmes.id"))
    academic_year_id: Mapped[str] = mapped_column(ForeignKey("academic_years.id"))
    number: Mapped[int] = mapped_column(Integer)

    __table_args__ = (
        UniqueConstraint("programme_id", "academic_year_id", "number"),
        CheckConstraint("number BETWEEN 1 AND 12"),
    )


class Section(Base):
    __tablename__ = "sections"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    semester_id: Mapped[str] = mapped_column(ForeignKey("semesters.id"))
    programme_id: Mapped[str] = mapped_column(ForeignKey("programmes.id"))
    name: Mapped[str] = mapped_column(String(30))
    student_count: Mapped[int] = mapped_column(Integer, default=0)

    programme = relationship("Programme", back_populates="sections")
    semester = relationship("Semester")

    @property
    def section_code(self) -> str:
        prog_code = self.programme.code if self.programme else "PROG"
        sem_num = self.semester.number if self.semester else "?"
        return f"{prog_code}-SEM{sem_num}-{self.name}"

    @property
    def display_name(self) -> str:
        prog_name = self.programme.name if self.programme else "Programme"
        sem_num = self.semester.number if self.semester else "?"
        return f"{prog_name} — Semester {sem_num} — Section {self.name}"

    @property
    def full_name(self) -> str:
        return self.display_name

    __table_args__ = (
        UniqueConstraint("semester_id", "name"),
        CheckConstraint("student_count >= 0"),
    )


class Subject(Base):
    __tablename__ = "subjects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    department_id: Mapped[str] = mapped_column(ForeignKey("departments.id"))
    programme_id: Mapped[str | None] = mapped_column(ForeignKey("programmes.id"), nullable=True)
    semester_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    semester_id: Mapped[str | None] = mapped_column(ForeignKey("semesters.id"), nullable=True)
    code: Mapped[str] = mapped_column(String(30))
    name: Mapped[str] = mapped_column(String(150))
    session_type: Mapped[SessionType] = mapped_column(Enum(SessionType))
    default_duration: Mapped[int] = mapped_column(Integer, default=60)

    department = relationship("Department")
    programme = relationship("Programme")
    semester = relationship("Semester")

    __table_args__ = (
        UniqueConstraint("department_id", "code"),
        CheckConstraint("default_duration > 0"),
    )


class Student(Base):
    __tablename__ = "students"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    student_id: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(150))
    email: Mapped[str] = mapped_column(String(255), unique=True)
    phone: Mapped[str | None] = mapped_column(String(30))
    whatsapp_number: Mapped[str | None] = mapped_column(String(30))
    admission_year: Mapped[int] = mapped_column(Integer)
    department_id: Mapped[str | None] = mapped_column(ForeignKey("departments.id"), nullable=True)
    programme_id: Mapped[str | None] = mapped_column(ForeignKey("programmes.id"), nullable=True)
    current_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    current_semester: Mapped[int | None] = mapped_column(Integer, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    whatsapp_consent: Mapped[bool] = mapped_column(Boolean, default=False)
    consent_at: Mapped[datetime | None] = mapped_column(DateTime)

    department = relationship("Department")
    programme = relationship("Programme")
    enrolments = relationship("Enrolment", back_populates="student")


class Faculty(Base):
    __tablename__ = "faculty"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    faculty_id: Mapped[str] = mapped_column(String(50), unique=True)
    department_id: Mapped[str] = mapped_column(ForeignKey("departments.id"))
    full_name: Mapped[str] = mapped_column(String(150))
    email: Mapped[str] = mapped_column(String(255), unique=True)
    phone: Mapped[str | None] = mapped_column(String(30))
    whatsapp_number: Mapped[str | None] = mapped_column(String(30))
    designation: Mapped[str | None] = mapped_column(String(100))
    highest_qualification: Mapped[str | None] = mapped_column(String(100), nullable=True)
    specialisation: Mapped[str | None] = mapped_column(String(150), nullable=True)
    max_classes_per_day: Mapped[int] = mapped_column(Integer, default=4)
    max_classes_per_week: Mapped[int] = mapped_column(Integer, default=18)
    max_consecutive_hours: Mapped[int] = mapped_column(Integer, default=2)
    min_break_minutes: Mapped[int] = mapped_column(Integer, default=15)
    cross_department_approved: Mapped[bool] = mapped_column(Boolean, default=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    whatsapp_consent: Mapped[bool] = mapped_column(Boolean, default=False)
    consent_at: Mapped[datetime | None] = mapped_column(DateTime)

    department = relationship("Department", back_populates="faculty")
    assignments = relationship("FacultyAssignment", back_populates="faculty")
    subject_eligibilities = relationship("FacultySubjectEligibility", back_populates="faculty", cascade="all, delete-orphan")
    semester_eligibilities = relationship("FacultySemesterEligibility", back_populates="faculty", cascade="all, delete-orphan")
    availability = relationship("FacultyAvailability", back_populates="faculty", cascade="all, delete-orphan")


class FacultySubjectEligibility(Base):
    __tablename__ = "faculty_subject_eligibilities"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    faculty_id: Mapped[str] = mapped_column(ForeignKey("faculty.id", ondelete="CASCADE"))
    subject_id: Mapped[str] = mapped_column(ForeignKey("subjects.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    faculty = relationship("Faculty", back_populates="subject_eligibilities")
    subject = relationship("Subject")

    __table_args__ = (
        UniqueConstraint("faculty_id", "subject_id"),
    )


class FacultySemesterEligibility(Base):
    __tablename__ = "faculty_semester_eligibilities"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    faculty_id: Mapped[str] = mapped_column(ForeignKey("faculty.id", ondelete="CASCADE"))
    semester_number: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    faculty = relationship("Faculty", back_populates="semester_eligibilities")

    __table_args__ = (
        UniqueConstraint("faculty_id", "semester_number"),
        CheckConstraint("semester_number BETWEEN 1 AND 12"),
    )


class Enrolment(Base):
    __tablename__ = "enrolments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    student_id: Mapped[str] = mapped_column(ForeignKey("students.id"))
    section_id: Mapped[str] = mapped_column(ForeignKey("sections.id"))
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    student = relationship("Student", back_populates="enrolments")

    __table_args__ = (
        UniqueConstraint("student_id", "section_id"),
    )


class FacultyAssignment(Base):
    __tablename__ = "faculty_assignments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    faculty_id: Mapped[str] = mapped_column(ForeignKey("faculty.id"))
    subject_id: Mapped[str] = mapped_column(ForeignKey("subjects.id"))
    section_id: Mapped[str] = mapped_column(ForeignKey("sections.id"))
    sessions_per_week: Mapped[int] = mapped_column(Integer, default=3)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=60)
    priority: Mapped[int] = mapped_column(Integer, default=5)
    required_capacity: Mapped[int] = mapped_column(Integer, default=0)
    required_room_type: Mapped[RoomType] = mapped_column(Enum(RoomType))
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    faculty = relationship("Faculty", back_populates="assignments")

    __table_args__ = (
        CheckConstraint("priority BETWEEN 1 AND 10"),
        CheckConstraint("sessions_per_week > 0"),
        CheckConstraint("duration_minutes > 0"),
    )


class Building(Base):
    __tablename__ = "buildings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    code: Mapped[str] = mapped_column(String(20), unique=True)
    available: Mapped[bool] = mapped_column(Boolean, default=True)

    floors = relationship("Floor", back_populates="building")


class Floor(Base):
    __tablename__ = "floors"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    building_id: Mapped[str] = mapped_column(ForeignKey("buildings.id"))
    name: Mapped[str] = mapped_column(String(50))
    level: Mapped[int] = mapped_column(Integer)

    building = relationship("Building", back_populates="floors")


class Room(Base):
    __tablename__ = "rooms"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    floor_id: Mapped[str] = mapped_column(ForeignKey("floors.id"))
    name: Mapped[str] = mapped_column(String(50))
    room_type: Mapped[RoomType] = mapped_column(Enum(RoomType))
    capacity: Mapped[int] = mapped_column(Integer)
    available: Mapped[bool] = mapped_column(Boolean, default=True)

    equipment: Mapped[list] = mapped_column(JSON, default=list)

    __table_args__ = (
        UniqueConstraint("floor_id", "name"),
        CheckConstraint("capacity > 0"),
    )


class CampusNode(Base):
    __tablename__ = "campus_nodes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(100))
    node_type: Mapped[str] = mapped_column(String(30))
    building_id: Mapped[str | None] = mapped_column(ForeignKey("buildings.id"))
    floor_id: Mapped[str | None] = mapped_column(ForeignKey("floors.id"))
    room_id: Mapped[str | None] = mapped_column(ForeignKey("rooms.id"), unique=True)


class CampusEdge(Base):
    __tablename__ = "campus_edges"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    source_id: Mapped[str] = mapped_column(ForeignKey("campus_nodes.id"))
    target_id: Mapped[str] = mapped_column(ForeignKey("campus_nodes.id"))
    distance: Mapped[float] = mapped_column(Float)
    connection_type: Mapped[str] = mapped_column(String(30))
    bidirectional: Mapped[bool] = mapped_column(Boolean, default=True)
    accessible: Mapped[bool] = mapped_column(Boolean, default=True)

    __table_args__ = (
        CheckConstraint("distance >= 0"),
    )


class FacultyAvailability(Base):
    __tablename__ = "faculty_availability"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    faculty_id: Mapped[str] = mapped_column(ForeignKey("faculty.id"))
    weekday: Mapped[int] = mapped_column(Integer)
    start_time: Mapped[time] = mapped_column(Time)
    end_time: Mapped[time] = mapped_column(Time)
    available: Mapped[bool] = mapped_column(Boolean, default=True)

    faculty = relationship("Faculty", back_populates="availability")

    __table_args__ = (
        CheckConstraint("weekday BETWEEN 0 AND 6"),
    )


class AvailabilityBlock(Base):
    __tablename__ = "availability_blocks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    resource_type: Mapped[AvailabilityType] = mapped_column(Enum(AvailabilityType))
    resource_id: Mapped[str] = mapped_column(String(36), index=True)
    start_at: Mapped[datetime] = mapped_column(DateTime)
    end_at: Mapped[datetime] = mapped_column(DateTime)
    reason: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class TimeSlot(Base):
    __tablename__ = "time_slots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    weekday: Mapped[int] = mapped_column(Integer)
    start_time: Mapped[time] = mapped_column(Time)
    end_time: Mapped[time] = mapped_column(Time)
    is_break: Mapped[bool] = mapped_column(Boolean, default=False)


class SchedulingDemand(Base):
    __tablename__ = "scheduling_demands"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    assignment_id: Mapped[str] = mapped_column(ForeignKey("faculty_assignments.id"))
    priority: Mapped[int] = mapped_column(Integer, default=5)
    duration_minutes: Mapped[int] = mapped_column(Integer)
    sessions_per_week: Mapped[int] = mapped_column(Integer)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    __table_args__ = (
        CheckConstraint("priority BETWEEN 1 AND 10"),
        CheckConstraint("duration_minutes > 0"),
    )


class TimetableVersion(Base):
    __tablename__ = "timetable_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    version_number: Mapped[int] = mapped_column(Integer)
    status: Mapped[VersionStatus] = mapped_column(
        Enum(VersionStatus), default=VersionStatus.DRAFT
    )
    algorithm: Mapped[str] = mapped_column(String(30))
    priority_weight: Mapped[float] = mapped_column(Float, default=0.65)
    sjf_weight: Mapped[float] = mapped_column(Float, default=0.35)
    quality_score: Mapped[float] = mapped_column(Float, default=0)
    statistics: Mapped[dict] = mapped_column(JSON, default=dict)
    programme_id: Mapped[str | None] = mapped_column(ForeignKey("programmes.id"), nullable=True)
    academic_year_id: Mapped[str | None] = mapped_column(ForeignKey("academic_years.id"), nullable=True)
    semester_id: Mapped[str | None] = mapped_column(ForeignKey("semesters.id"), nullable=True)
    section_id: Mapped[str | None] = mapped_column(ForeignKey("sections.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    published_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_by: Mapped[str | None] = mapped_column(ForeignKey("admins.id"))
    approved_by: Mapped[str | None] = mapped_column(ForeignKey("admins.id"))

    programme = relationship("Programme")
    academic_year = relationship("AcademicYear")
    semester = relationship("Semester")
    section = relationship("Section")


class ScheduledClass(Base):
    __tablename__ = "scheduled_classes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    version_id: Mapped[str] = mapped_column(
        ForeignKey("timetable_versions.id", ondelete="CASCADE"), index=True
    )
    assignment_id: Mapped[str] = mapped_column(ForeignKey("faculty_assignments.id"))
    faculty_id: Mapped[str] = mapped_column(ForeignKey("faculty.id"), index=True)
    section_id: Mapped[str] = mapped_column(ForeignKey("sections.id"), index=True)
    subject_id: Mapped[str] = mapped_column(ForeignKey("subjects.id"))
    room_id: Mapped[str] = mapped_column(ForeignKey("rooms.id"), index=True)
    weekday: Mapped[int] = mapped_column(Integer)
    start_minute: Mapped[int] = mapped_column(Integer)
    end_minute: Mapped[int] = mapped_column(Integer)
    session_number: Mapped[int] = mapped_column(Integer)
    manual_override: Mapped[bool] = mapped_column(Boolean, default=False)

    __table_args__ = (
        CheckConstraint("weekday BETWEEN 0 AND 6"),
        CheckConstraint("start_minute >= 0"),
        CheckConstraint("end_minute > start_minute"),
        UniqueConstraint("version_id", "section_id", "weekday",
                         "start_minute", "end_minute",
                         name="uq_section_exact_slot"),
        Index("ix_schedule_version_day", "version_id", "weekday"),
    )


class SchedulingRun(Base):
    __tablename__ = "scheduling_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    version_id: Mapped[str | None] = mapped_column(ForeignKey("timetable_versions.id"))
    mode: Mapped[str] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(30))
    objective_value: Mapped[float | None] = mapped_column(Float)
    solver_status: Mapped[str | None] = mapped_column(String(50))
    duration_seconds: Mapped[float | None] = mapped_column(Float)
    unscheduled: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Approval(Base):
    __tablename__ = "approvals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    version_id: Mapped[str] = mapped_column(ForeignKey("timetable_versions.id"))
    admin_id: Mapped[str] = mapped_column(ForeignKey("admins.id"))
    decision: Mapped[str] = mapped_column(String(30))
    comments: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    admin_id: Mapped[str | None] = mapped_column(ForeignKey("admins.id"))
    action: Mapped[str] = mapped_column(String(100), index=True)
    entity_type: Mapped[str] = mapped_column(String(100))
    entity_id: Mapped[str | None] = mapped_column(String(36))
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class TimetableImage(Base):
    __tablename__ = "timetable_images"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    version_id: Mapped[str] = mapped_column(ForeignKey("timetable_versions.id"))
    recipient_type: Mapped[str] = mapped_column(String(20))
    recipient_id: Mapped[str] = mapped_column(String(36))
    file_path: Mapped[str] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class WhatsAppNotification(Base):
    __tablename__ = "whatsapp_notifications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    image_id: Mapped[str | None] = mapped_column(ForeignKey("timetable_images.id"))
    recipient_type: Mapped[str] = mapped_column(String(20))
    recipient_id: Mapped[str] = mapped_column(String(36))
    phone_number: Mapped[str] = mapped_column(String(30))
    message_id: Mapped[str | None] = mapped_column(String(150), unique=True)
    status: Mapped[DeliveryStatus] = mapped_column(
        Enum(DeliveryStatus), default=DeliveryStatus.QUEUED
    )
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class WhatsAppDeliveryEvent(Base):
    __tablename__ = "whatsapp_delivery_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    notification_id: Mapped[str] = mapped_column(
        ForeignKey("whatsapp_notifications.id"), index=True
    )
    status: Mapped[str] = mapped_column(String(30))
    event_timestamp: Mapped[datetime] = mapped_column(DateTime)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)


class ReschedulingEvent(Base):
    __tablename__ = "rescheduling_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    old_version_id: Mapped[str] = mapped_column(ForeignKey("timetable_versions.id"))
    new_version_id: Mapped[str | None] = mapped_column(ForeignKey("timetable_versions.id"))
    reason: Mapped[str] = mapped_column(Text)
    affected_classes: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(30), default="PROPOSED")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class EmailNotification(Base):
    __tablename__ = "email_notifications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    version_id: Mapped[str] = mapped_column(ForeignKey("timetable_versions.id"), index=True)
    image_id: Mapped[str | None] = mapped_column(ForeignKey("timetable_images.id"))
    recipient_type: Mapped[str] = mapped_column(String(20))
    recipient_id: Mapped[str] = mapped_column(String(36))
    recipient_email: Mapped[str] = mapped_column(String(255))
    subject: Mapped[str] = mapped_column(String(255))
    status: Mapped[DeliveryStatus] = mapped_column(
        Enum(DeliveryStatus), default=DeliveryStatus.QUEUED
    )
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime)

    deliveries = relationship("NotificationDelivery", back_populates="notification")


class NotificationDelivery(Base):
    __tablename__ = "notification_deliveries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    notification_id: Mapped[str] = mapped_column(
        ForeignKey("email_notifications.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(String(30))
    delivery_timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    details: Mapped[dict] = mapped_column(JSON, default=dict)

    notification = relationship("EmailNotification", back_populates="deliveries")


class SchedulingLock(Base):
    __tablename__ = "scheduling_locks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    scope: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False)
    locked_by: Mapped[str | None] = mapped_column(String(100))
    locked_at: Mapped[datetime | None] = mapped_column(DateTime)
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=300)
