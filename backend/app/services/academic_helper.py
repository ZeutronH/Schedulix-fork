def format_section_identity(
    section_name: str,
    programme_name: str | None = None,
    programme_code: str | None = None,
    semester_number: int | None = None
) -> dict:
    code_part = (programme_code or "PROG").strip().upper()
    sem_part = f"SEM{semester_number}" if semester_number is not None else "SEM?"
    prog_name_part = (programme_name or "Programme").strip()
    sem_name_part = f"Semester {semester_number}" if semester_number is not None else "Semester"
    sec_name = (section_name or "").strip()

    section_code = f"{code_part}-{sem_part}-{sec_name}"
    display_name = f"{prog_name_part} — {sem_name_part} — Section {sec_name}"

    return {
        "section_code": section_code,
        "section_display_name": display_name,
        "display_name": display_name,
        "full_name": display_name
    }
