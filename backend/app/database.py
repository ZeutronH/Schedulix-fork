from sqlalchemy import create_engine
from sqlalchemy.orm import (
    DeclarativeBase,
    sessionmaker,
)
from app.config import settings


class Base(DeclarativeBase):
    pass


engine = create_engine(
    settings.effective_database_url,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    isolation_level="READ COMMITTED",
)


SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()