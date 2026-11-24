import os
import re
from datetime import datetime

from PIL import Image, ImageDraw, ImageFont
from sqlalchemy import select

from app.config import settings
from app.models import (
    TimetableVersion,
    TimetableImage,
    Section,
    Faculty,
    Programme,
    Department,
    Semester,
    AcademicYear
)
from app.services.timetable import (
    section_timetable,
    faculty_timetable,
)

DAYS = ["Monday", "Tuesday", "Wednesday",
        "Thursday", "Friday", "Saturday", "Sunday"]


def get_font(size, bold=False):
    paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        if bold else
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"
        if bold else
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
        "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf"
        if bold else
        "/usr/share/fonts/TTF/DejaVuSans.ttf"
    ]

    for path in paths:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass

    return ImageFont.load_default()


def sanitize(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]", "_", text).strip("_").upper()


def generate_timetable_png(
    db,
    version_id,
    recipient_type,
    recipient_id
):
    version = db.get(TimetableVersion, version_id)
    if not version:
        raise ValueError("Timetable version not found")

    dept_name = "Department"
    dept_code = "UNIV"
    prog_name = "Undergraduate Programme"
    prog_code = "UG"
    sem_num = 1
    acad_year = str(datetime.now().year)
    section_name = "A"
    recipient_display = ""
    subtitle = ""

    if recipient_type == "STUDENT":
        recipient = db.get(Section, recipient_id)
        if not recipient:
            raise ValueError("Section not found")

        classes = section_timetable(db, version_id, recipient_id)
        section_name = recipient.name
        recipient_display = f"Section: {section_name}"

        programme = db.get(Programme, recipient.programme_id) if recipient.programme_id else None
        if programme:
            prog_name = programme.name
            prog_code = programme.code
            dept = db.get(Department, programme.department_id) if programme.department_id else None
            if dept:
                dept_name = dept.name
                dept_code = dept.code

        semester = db.get(Semester, recipient.semester_id) if recipient.semester_id else None
        if semester:
            sem_num = semester.number
            year_record = db.get(AcademicYear, semester.academic_year_id) if semester.academic_year_id else None
            if year_record:
                acad_year = year_record.name

        filename = f"{sanitize(dept_code)}_{sanitize(prog_code)}_SEM{sem_num}_SECTION_{sanitize(section_name)}_{sanitize(acad_year)}.png"
        subtitle = f"{dept_name} • {prog_name} • Semester {sem_num} • {acad_year}"

    elif recipient_type == "FACULTY":
        recipient = db.get(Faculty, recipient_id)
        if not recipient:
            raise ValueError("Faculty not found")

        classes = faculty_timetable(db, version_id, recipient_id)
        recipient_display = f"Faculty: {recipient.full_name} ({recipient.faculty_id})"
        subtitle = f"{recipient.designation or 'Faculty Member'} • Version {version.version_number}"
        filename = f"FACULTY_{sanitize(recipient.faculty_id)}_{sanitize(acad_year)}.png"

    else:
        raise ValueError("Invalid recipient type")

    # Image dimensions
    width, height = 1800, 1100
    image = Image.new("RGB", (width, height), "#F8FAFC")
    draw = ImageDraw.Draw(image)

    font_title = get_font(34, True)
    font_subtitle = get_font(18, False)
    font_header = get_font(18, True)
    font_card_title = get_font(16, True)
    font_card_text = get_font(14, False)

    # 1. Header Banner
    draw.rounded_rectangle((30, 25, width - 30, 150), radius=16, fill="#1E293B")
    draw.text((55, 45), settings.UNIVERSITY_NAME or "SCHEDULIX UNIVERSITY", fill="#FFFFFF", font=font_title)
    draw.text((55, 90), f"{recipient_display} | {subtitle}", fill="#94A3B8", font=font_subtitle)
    draw.text((width - 320, 50), f"TIMETABLE VERSION {version.version_number}", fill="#38BDF8", font=font_header)
    draw.text((width - 320, 85), f"Status: {version.status.value}", fill="#A7F3D0", font=font_subtitle)

    # 2. Weekdays table layout: Monday (0) to Friday (4) or Saturday (5)
    max_day = max([c["weekday"] for c in classes] + [4])
    active_days = list(range(max_day + 1))

    num_days = len(active_days)
    left_margin = 40
    right_margin = width - 40
    top_margin = 175
    bottom_margin = height - 50

    col_width = (right_margin - left_margin) / num_days

    for col_idx, day_num in enumerate(active_days):
        col_x = left_margin + col_idx * col_width
        day_name = DAYS[day_num]

        # Column Header Box
        draw.rounded_rectangle(
            (col_x + 4, top_margin, col_x + col_width - 4, top_margin + 45),
            radius=8,
            fill="#3B82F6" if day_num < 5 else "#6366F1"
        )
        draw.text(
            (col_x + 16, top_margin + 12),
            day_name.upper(),
            fill="#FFFFFF",
            font=font_header
        )

        # Draw classes for this day
        day_classes = [c for c in classes if c["weekday"] == day_num]
        day_classes.sort(key=lambda c: c["start_minute"])

        card_y = top_margin + 55
        if not day_classes:
            draw.rounded_rectangle(
                (col_x + 4, card_y, col_x + col_width - 4, card_y + 60),
                radius=8,
                fill="#FFFFFF",
                outline="#E2E8F0",
                width=1
            )
            draw.text((col_x + 16, card_y + 20), "No Classes Scheduled", fill="#94A3B8", font=font_card_text)
        else:
            for c in day_classes:
                card_height = 110
                if card_y + card_height > bottom_margin:
                    break

                # Session Type Color Accent
                border_color = "#3B82F6" if c.get("session_type") == "LABORATORY" else "#10B981"
                bg_color = "#FFFFFF"

                # Card background
                draw.rounded_rectangle(
                    (col_x + 4, card_y, col_x + col_width - 4, card_y + card_height),
                    radius=8,
                    fill=bg_color,
                    outline=border_color,
                    width=2
                )

                # Subject Code & Name
                subj_line = f"{c.get('subject_code', '')}: {c.get('subject', '')}"[:32]
                draw.text((col_x + 14, card_y + 10), subj_line, fill="#1E293B", font=font_card_title)

                # Time slot
                time_line = f"🕒 {c.get('start', '')} - {c.get('end', '')} ({c.get('duration', 60)}m)"
                draw.text((col_x + 14, card_y + 36), time_line, fill="#475569", font=font_card_text)

                # Faculty or Section Detail
                if recipient_type == "FACULTY":
                    detail_line = f"👥 {c.get('section_code') or c.get('section', '')}"[:30]
                else:
                    detail_line = f"👤 {c.get('faculty', '')}"[:30]
                draw.text((col_x + 14, card_y + 60), detail_line, fill="#475569", font=font_card_text)

                # Classroom
                room_line = f"📍 {c.get('room', '')} ({c.get('building', '')})"[:30]
                draw.text((col_x + 14, card_y + 84), room_line, fill="#2563EB", font=font_card_text)

                card_y += card_height + 10

    # Footer note
    draw.text(
        (left_margin, height - 35),
        f"Generated by Schedulix • Relational DBMS & OS Scheduling Engine • {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        fill="#94A3B8",
        font=font_card_text
    )

    directory = os.path.join(settings.MEDIA_DIRECTORY, "timetables", version_id)
    os.makedirs(directory, exist_ok=True)
    full_path = os.path.join(directory, filename)

    image.save(full_path, "PNG", optimize=True)

    # Persist or update record in database
    existing_image = db.scalars(
        select(TimetableImage).where(
            TimetableImage.version_id == version_id,
            TimetableImage.recipient_type == recipient_type,
            TimetableImage.recipient_id == recipient_id
        )
    ).first()

    if existing_image:
        existing_image.file_path = full_path
        record = existing_image
    else:
        record = TimetableImage(
            version_id=version_id,
            recipient_type=recipient_type,
            recipient_id=recipient_id,
            file_path=full_path
        )
        db.add(record)

    db.flush()
    return record


def generate_faculty_weekly_png(db, faculty_id: str, classes: list | None = None) -> tuple[str, str]:
    """
    Generates a consolidated weekly schedule PNG for an individual faculty member,
    combining all classes across different sections and programmes.
    Returns (full_path, filename).
    """
    faculty = db.get(Faculty, faculty_id)
    if not faculty:
        raise ValueError("Faculty not found")

    dept = db.get(Department, faculty.department_id) if faculty.department_id else None
    dept_name = dept.name if dept else "Academic Department"
    year_str = str(datetime.now().year)

    if classes is None:
        classes = []

    width, height = 1800, 1100
    image = Image.new("RGB", (width, height), "#F8FAFC")
    draw = ImageDraw.Draw(image)

    font_title = get_font(34, True)
    font_subtitle = get_font(18, False)
    font_header = get_font(18, True)
    font_card_title = get_font(16, True)
    font_card_text = get_font(14, False)

    # 1. Header Banner
    draw.rounded_rectangle((30, 25, width - 30, 150), radius=16, fill="#1E293B")
    draw.text((55, 45), settings.UNIVERSITY_NAME or "SCHEDULIX UNIVERSITY", fill="#FFFFFF", font=font_title)
    draw.text((55, 90), f"Faculty Timetable: {faculty.full_name} ({faculty.faculty_id}) | {faculty.designation or 'Faculty'} • {dept_name}", fill="#94A3B8", font=font_subtitle)
    draw.text((width - 320, 50), f"ACADEMIC YEAR {year_str}", fill="#38BDF8", font=font_header)
    draw.text((width - 320, 85), f"Total Classes: {len(classes)} / week", fill="#A7F3D0", font=font_subtitle)

    # 2. Weekdays table layout: Monday (0) to Friday (4) or Saturday (5)
    max_day = max([c["weekday"] for c in classes] + [4])
    active_days = list(range(max_day + 1))
    num_days = len(active_days)
    left_margin = 40
    right_margin = width - 40
    top_margin = 175
    bottom_margin = height - 50
    col_width = (right_margin - left_margin) / num_days

    for col_idx, day_num in enumerate(active_days):
        col_x = left_margin + col_idx * col_width
        day_name = DAYS[day_num]

        # Column Header Box
        draw.rounded_rectangle(
            (col_x + 4, top_margin, col_x + col_width - 4, top_margin + 45),
            radius=8,
            fill="#3B82F6" if day_num < 5 else "#6366F1"
        )
        draw.text((col_x + 16, top_margin + 12), day_name.upper(), fill="#FFFFFF", font=font_header)

        # Classes for this day
        day_classes = [c for c in classes if c["weekday"] == day_num]
        day_classes.sort(key=lambda c: c["start_minute"])

        card_y = top_margin + 55
        if not day_classes:
            draw.rounded_rectangle(
                (col_x + 4, card_y, col_x + col_width - 4, card_y + 60),
                radius=8, fill="#FFFFFF", outline="#E2E8F0", width=1
            )
            draw.text((col_x + 16, card_y + 20), "No Classes Scheduled", fill="#94A3B8", font=font_card_text)
        else:
            for c in day_classes:
                card_height = 110
                if card_y + card_height > bottom_margin:
                    break

                border_color = "#3B82F6" if c.get("session_type") == "LABORATORY" else "#10B981"
                draw.rounded_rectangle(
                    (col_x + 4, card_y, col_x + col_width - 4, card_y + card_height),
                    radius=8, fill="#FFFFFF", outline=border_color, width=2
                )
                subj_line = f"{c.get('subject_code', '')}: {c.get('subject', '')}"[:32]
                draw.text((col_x + 14, card_y + 10), subj_line, fill="#1E293B", font=font_card_title)

                time_line = f"🕒 {c.get('start', '')} - {c.get('end', '')} ({c.get('duration', 60)}m)"
                draw.text((col_x + 14, card_y + 36), time_line, fill="#475569", font=font_card_text)

                sec_line = f"👥 {c.get('section_code') or c.get('section', '')}"[:30]
                draw.text((col_x + 14, card_y + 60), sec_line, fill="#475569", font=font_card_text)

                room_line = f"📍 {c.get('room', '')} ({c.get('building', '')})"[:30]
                draw.text((col_x + 14, card_y + 84), room_line, fill="#2563EB", font=font_card_text)

                card_y += card_height + 10

    # Footer note
    draw.text(
        (left_margin, height - 35),
        f"Generated by Schedulix • Faculty Timetable Portal • {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        fill="#94A3B8",
        font=font_card_text
    )

    directory = os.path.join(settings.MEDIA_DIRECTORY, "timetables", "faculty")
    os.makedirs(directory, exist_ok=True)
    filename = f"Faculty_Timetable_{sanitize(faculty.faculty_id)}_{year_str}.png"
    full_path = os.path.join(directory, filename)

    image.save(full_path, "PNG", optimize=True)
    return full_path, filename
