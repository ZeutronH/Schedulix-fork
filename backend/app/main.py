import os

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.middleware import SlowAPIMiddleware

from app.config import settings

from app.routers import (
    auth,
    academic,
    campus,
    scheduling,
    availability,
    whatsapp,
    notifications,
    os_demo,
    audit,
    student_portal,
    faculty_portal,
)


os.makedirs(settings.MEDIA_DIRECTORY, exist_ok=True)

limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title=settings.APP_NAME,
    description="University Timetable Management System",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

app.state.limiter = limiter

app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-Hub-Signature-256"],
)

app.mount(
    "/media",
    StaticFiles(directory=settings.MEDIA_DIRECTORY),
    name="media"
)

app.include_router(auth.router, prefix="/api")
app.include_router(academic.router, prefix="/api")
app.include_router(campus.router, prefix="/api")
app.include_router(scheduling.router, prefix="/api")
app.include_router(availability.router, prefix="/api")
app.include_router(whatsapp.router, prefix="/api")
app.include_router(notifications.router, prefix="/api")
app.include_router(student_portal.router, prefix="/api")
app.include_router(faculty_portal.router, prefix="/api")
app.include_router(os_demo.router, prefix="/api")
app.include_router(audit.router, prefix="/api")


@app.get("/")
def root():
    return {
        "application": settings.APP_NAME,
        "version": "1.0.0",
        "status": "RUNNING"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "whatsapp_configured": bool(
            settings.WHATSAPP_ENABLED
            and settings.WHATSAPP_ACCESS_TOKEN
        )
    }