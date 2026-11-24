from datetime import time, date, datetime
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict, EmailStr, model_validator


# ============================================================
# AUTHENTICATION
# ============================================================

class LoginRequest(BaseModel):
    username: str
    password: str


class AdminCreate(BaseModel):
    username: str
    email: EmailStr
    password: str = Field(min_length=12)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: Optional[str] = None


# ============================================================
# DEPARTMENTS AND PROGRAMMES
# ============================================================

class DepartmentCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    code: str = Field(min_length=2, max_length=20)
    description: Optional[str] = None


class ProgrammeCreate(BaseModel):
    department_id: str
    name: str
    code: str
    duration_years: int = Field(ge=1, le=10)


class ProgrammeUpdate(BaseModel):
    department_id: Optional[str] = None
    name: Optional[str] = None
    code: Optional[str] = None
    duration_years: Optional[int] = Field(default=None, ge=1, le=10)


# ============================================================
# ACADEMIC YEAR, SEMESTER AND SECTION
# ============================================================

class AcademicYearCreate(BaseModel):
    name: str
    start_date: date
    end_date: date


class SectionCreate(BaseModel):
    semester_id: str
    programme_id: str
    name: str
    student_count: int = Field(ge=0)


# ============================================================
# SUBJECTS
# ============================================================

class SubjectCreate(BaseModel):
    department_id: str
    programme_id: Optional[str] = None
    semester_number: Optional[int] = None
    semester_id: Optional[str] = None
    code: str = Field(min_length=2, max_length=30)
    name: str
    session_type: str
    default_duration: int = Field(gt=0, le=480)


class SubjectUpdate(BaseModel):
    department_id: Optional[str] = None
    programme_id: Optional[str] = None
    semester_number: Optional[int] = None
    semester_id: Optional[str] = None
    code: Optional[str] = None
    name: Optional[str] = None
    session_type: Optional[str] = None
    default_duration: Optional[int] = None


# ============================================================
# STUDENTS
# ============================================================

class StudentCreate(BaseModel):
    # Generated automatically when omitted.
    student_id: Optional[str] = None

    full_name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    password: Optional[str] = None

    admission_year: int = Field(ge=2000, le=2100)

    department_id: Optional[str] = None
    programme_id: Optional[str] = None
    current_year: Optional[int] = None
    current_semester: Optional[int] = None
    section_id: Optional[str] = None

    phone: Optional[str] = None
    whatsapp_number: Optional[str] = None


class StudentLoginRequest(BaseModel):
    identifier: str = Field(min_length=1, description="Student ID or Email")
    password: str = Field(min_length=1, description="Student password")


class FacultyLoginRequest(BaseModel):
    identifier: str = Field(min_length=1, description="Faculty ID or Email")
    password: str = Field(min_length=1, description="Faculty password")


class FacultyPasswordResetRequest(BaseModel):
    new_password: Optional[str] = None


class StudentUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    whatsapp_number: Optional[str] = None
    department_id: Optional[str] = None
    programme_id: Optional[str] = None
    current_year: Optional[int] = None
    current_semester: Optional[int] = None
    active: Optional[bool] = None


class StudentTransferRequest(BaseModel):
    new_section_id: str


# ============================================================
# FACULTY
# ============================================================

class FacultyCreate(BaseModel):
    # Generated automatically when omitted.
    faculty_id: Optional[str] = None

    department_id: str
    full_name: str = Field(min_length=2, max_length=150)
    email: EmailStr

    phone: Optional[str] = None
    whatsapp_number: Optional[str] = None
    designation: Optional[str] = None
    highest_qualification: Optional[str] = None
    specialisation: Optional[str] = None
    max_classes_per_day: Optional[int] = Field(default=4, ge=1, le=12)
    max_classes_per_week: Optional[int] = Field(default=18, ge=1, le=48)
    max_consecutive_hours: Optional[int] = Field(default=2, ge=1, le=8)
    min_break_minutes: Optional[int] = Field(default=15, ge=0, le=120)
    cross_department_approved: Optional[bool] = False
    password: Optional[str] = None
    eligible_subject_ids: Optional[list[str]] = None
    eligible_semesters: Optional[list[int]] = None


class FacultyUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    department_id: Optional[str] = None
    phone: Optional[str] = None
    whatsapp_number: Optional[str] = None
    designation: Optional[str] = None
    highest_qualification: Optional[str] = None
    specialisation: Optional[str] = None
    max_classes_per_day: Optional[int] = Field(default=None, ge=1, le=12)
    max_classes_per_week: Optional[int] = Field(default=None, ge=1, le=48)
    max_consecutive_hours: Optional[int] = Field(default=None, ge=1, le=8)
    min_break_minutes: Optional[int] = Field(default=None, ge=0, le=120)
    cross_department_approved: Optional[bool] = None
    password: Optional[str] = None
    active: Optional[bool] = None


class FacultyEligibilityUpdate(BaseModel):
    subject_ids: list[str] = Field(default_factory=list)
    eligible_semesters: list[int] = Field(default_factory=list)
    cross_department_approved: Optional[bool] = None


# ============================================================
# FACULTY ASSIGNMENTS
# ============================================================

class AssignmentCreate(BaseModel):
    faculty_id: str
    subject_id: str
    section_id: str

    sessions_per_week: int = Field(ge=1, le=20)
    duration_minutes: int = Field(gt=0, le=480)

    priority: int = Field(ge=1, le=10)
    required_capacity: int = Field(ge=1)

    required_room_type: str


# ============================================================
# CAMPUS AND CLASSROOMS
# ============================================================

class RoomCreate(BaseModel):
    floor_id: str

    name: str = Field(min_length=1, max_length=50)
    room_type: str

    capacity: int = Field(gt=0)

    equipment: list[str] = Field(default_factory=list)


class CampusNodeCreate(BaseModel):
    name: str
    node_type: str

    building_id: Optional[str] = None
    floor_id: Optional[str] = None
    room_id: Optional[str] = None


class CampusEdgeCreate(BaseModel):
    source_id: str
    target_id: str

    distance: float = Field(ge=0)

    connection_type: str

    bidirectional: bool = True
    accessible: bool = True


# ============================================================
# SCHEDULING
# ============================================================

class ScheduleRequest(BaseModel):
    mode: str = "HYBRID"

    priority_weight: float = Field(
        default=0.65,
        ge=0,
        le=1
    )

    sjf_weight: float = Field(
        default=0.35,
        ge=0,
        le=1
    )

    weekdays: list[int] = Field(
        default_factory=lambda: [0, 1, 2, 3, 4, 5]
    )

    day_start: time = time(8, 0)
    day_end: time = time(18, 0)

    time_limit_seconds: int = Field(
        default=30,
        ge=1,
        le=300
    )
    max_solver_seconds: Optional[int] = None

    @model_validator(mode="before")
    @classmethod
    def handle_time_limit_aliases(cls, data):
        if isinstance(data, dict):
            if "max_solver_seconds" in data and "time_limit_seconds" not in data:
                data["time_limit_seconds"] = data["max_solver_seconds"]
        return data

    programme_id: Optional[str] = None
    academic_year_id: Optional[str] = None
    semester_id: Optional[str] = None
    section_id: Optional[str] = None


# ============================================================
# APPROVALS
# ============================================================

class ApprovalRequest(BaseModel):
    comments: Optional[str] = None


# ============================================================
# AVAILABILITY
# ============================================================

class AvailabilityCreate(BaseModel):
    resource_type: str
    resource_id: str

    start_at: datetime
    end_at: datetime

    reason: str


class OverrideRequest(BaseModel):
    class_id: str
    room_id: str

    weekday: int = Field(ge=0, le=6)

    start_minute: int = Field(
        ge=0,
        lt=1440
    )


class ConflictCheckRequest(BaseModel):
    version_id: str
    class_id: str
    new_weekday: int = Field(ge=0, le=6)
    new_start_minute: int = Field(ge=0, lt=1440)
    new_end_minute: int = Field(ge=0, lt=1440)
    new_room_id: Optional[str] = None
    new_faculty_id: Optional[str] = None


class ManualRescheduleRequest(BaseModel):
    class_id: str
    new_weekday: int = Field(ge=0, le=6)
    new_start_minute: int = Field(ge=0, lt=1440)
    new_end_minute: int = Field(ge=0, lt=1440)
    new_room_id: Optional[str] = None
    new_faculty_id: Optional[str] = None
    reason: str = "Manual administrative adjustment"


# ============================================================
# COMMON RESPONSE MODEL
# ============================================================

class OutputModel(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )