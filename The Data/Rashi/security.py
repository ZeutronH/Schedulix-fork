from datetime import datetime, timedelta, timezone

from jose import jwt, JWTError
from passlib.context import CryptContext

from app.config import settings

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)

ALGORITHM = "HS256"


def hash_password(password: str, min_length: int = 6) -> str:
    if len(password) < min_length:
        raise ValueError(f"Password must contain at least {min_length} characters")
    return pwd_context.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    if not hashed:
        return False
    return pwd_context.verify(password, hashed)


def create_access_token(subject: str, role: str = "ADMIN"):
    expiry = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )

    return jwt.encode(
        {"sub": subject, "role": role, "exp": expiry},
        settings.SECRET_KEY,
        algorithm=ALGORITHM
    )


def decode_access_token(token: str):
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[ALGORITHM]
        )
        return payload.get("sub")
    except JWTError:
        return None


def decode_token_payload(token: str) -> dict | None:
    try:
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[ALGORITHM]
        )
    except JWTError:
        return None