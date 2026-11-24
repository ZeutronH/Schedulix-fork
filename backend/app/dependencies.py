from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Admin, Student, Faculty
from app.security import decode_token_payload

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")


def get_current_admin(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    payload = decode_token_payload(token)

    if not payload or not payload.get("sub"):
        raise HTTPException(401, "Invalid or expired token")

    role = payload.get("role")
    if role != "ADMIN":
        raise HTTPException(403, "Administrator privileges required")

    admin_id = payload.get("sub")
    admin = db.get(Admin, admin_id)

    if not admin or not admin.active:
        raise HTTPException(401, "Administrator account unavailable")

    return admin


def get_current_faculty(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    payload = decode_token_payload(token)

    if not payload or not payload.get("sub"):
        raise HTTPException(401, "Invalid or expired token")

    if payload.get("role") != "FACULTY":
        raise HTTPException(403, "Faculty access required")

    faculty_id = payload.get("sub")
    faculty = db.get(Faculty, faculty_id)

    if not faculty or not faculty.active:
        raise HTTPException(401, "Faculty account inactive or not found")

    return faculty


def get_current_student(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    payload = decode_token_payload(token)

    if not payload or not payload.get("sub"):
        raise HTTPException(401, "Invalid or expired token")

    if payload.get("role") != "STUDENT":
        raise HTTPException(403, "Student access required")

    student_id = payload.get("sub")
    student = db.get(Student, student_id)

    if not student or not student.active:
        raise HTTPException(401, "Student account inactive or not found")

    return student


def get_authenticated_entity(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    Returns (user_type, entity) where user_type is 'ADMIN', 'FACULTY', or 'STUDENT'.
    """
    payload = decode_token_payload(token)
    if not payload or not payload.get("sub"):
        raise HTTPException(401, "Invalid or expired token")

    sub = payload.get("sub")
    role = payload.get("role")

    if role == "STUDENT":
        student = db.get(Student, sub)
        if not student or not student.active:
            raise HTTPException(401, "Student account inactive")
        return "STUDENT", student
    elif role == "FACULTY":
        faculty = db.get(Faculty, sub)
        if not faculty or not faculty.active:
            raise HTTPException(401, "Faculty account inactive")
        return "FACULTY", faculty
    else:
        admin = db.get(Admin, sub)
        if not admin or not admin.active:
            raise HTTPException(401, "Admin account inactive")
        return "ADMIN", admin
