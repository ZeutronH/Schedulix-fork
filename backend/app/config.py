import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    APP_NAME: str = "Schedulix"
    ENVIRONMENT: str = "development"

    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    ADMIN_USERNAME: str = "admin"
    ADMIN_EMAIL: str = "admin@example.com"
    ADMIN_PASSWORD: str = "admin123456789"

    DATABASE_URL: str
    REDIS_URL: str = "redis://localhost:6379/0"

    CORS_ORIGINS: str = "http://localhost:5173"

    UNIVERSITY_NAME: str = "Your University"
    UNIVERSITY_LOGO: str = ""

    SCHEDULING_MODE: str = "HYBRID"
    PRIORITY_WEIGHT: float = 0.65
    SJF_WEIGHT: float = 0.35
    SCHEDULING_TIME_LIMIT: int = 30

    WHATSAPP_ENABLED: bool = False
    WHATSAPP_ACCESS_TOKEN: str = ""
    WHATSAPP_PHONE_NUMBER_ID: str = ""
    WHATSAPP_BUSINESS_ACCOUNT_ID: str = ""
    WHATSAPP_VERIFY_TOKEN: str = ""
    WHATSAPP_APP_SECRET: str = ""
    WHATSAPP_TEMPLATE_NAME: str = "timetable_notification"
    WHATSAPP_TEMPLATE_LANGUAGE: str = "en"

    MEDIA_DIRECTORY: str = "media"

    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "schedulix@university.edu"
    SMTP_USE_TLS: bool = True
    EMAIL_ENABLED: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )

    @property
    def cors_list(self):
        origins = {
            origin.strip()
            for origin in self.CORS_ORIGINS.split(",")
            if origin.strip()
        }
        origins.update([
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:5174",
            "http://127.0.0.1:5174",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:8000",
            "http://127.0.0.1:8000",
            "http://localhost:8001",
            "http://127.0.0.1:8001",
        ])
        return list(origins)

    @property
    def effective_database_url(self) -> str:
        url = self.DATABASE_URL
        if os.path.exists("/.dockerenv"):
            if ".pgdata" in url or "localhost" in url or "127.0.0.1" in url:
                return "postgresql+psycopg://schedulix:schedulix_dev@db:5432/schedulix"
            return url
        if "@db:5432" in url:
            return "postgresql+psycopg://schedulix:schedulix_dev@localhost:5433/schedulix"
        return url

    @property
    def effective_redis_url(self) -> str:
        url = self.REDIS_URL
        if os.path.exists("/.dockerenv"):
            if "localhost" in url or "127.0.0.1" in url or "redis.sock" in url:
                return "redis://redis:6379/0"
            return url
        if "redis://redis:6379" in url:
            return "redis://localhost:6379/0"
        return url


@lru_cache
def get_settings():
    return Settings()


settings = get_settings()