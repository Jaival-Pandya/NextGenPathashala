"""Application configuration. Secrets and database URLs come from environment variables."""
import os
from datetime import timedelta

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:  # Render sets environment variables directly.
    pass


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def normalize_database_url(url: str) -> str:
    """Normalize platform-provided PostgreSQL URLs for psycopg 3.

    The project installs psycopg 3, so explicitly select SQLAlchemy's
    ``postgresql+psycopg`` dialect instead of relying on its psycopg2 default.
    """
    if url.startswith("postgres://"):
        url = "postgresql://" + url.removeprefix("postgres://")
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url.removeprefix("postgresql://")
    return url


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-change-me-before-deploying")
    APP_ENV = os.environ.get("APP_ENV", "development").strip().lower()
    SQLALCHEMY_DATABASE_URI = normalize_database_url(
        os.environ.get("DATABASE_URL", "sqlite:///nextgenpathashala.db")
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}
    WTF_CSRF_TIME_LIMIT = 3600
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = _as_bool(os.environ.get("SESSION_COOKIE_SECURE"), os.environ.get("RENDER") is not None)
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 MiB request limit; configure separately for object storage uploads.
    AUTO_CREATE_DB = _as_bool(os.environ.get("AUTO_CREATE_DB"), False)
    PILOT_ADMIN_EMAIL = os.environ.get("PILOT_ADMIN_EMAIL", "").strip().lower()
    RATELIMIT_STORAGE_URI = os.environ.get("RATELIMIT_STORAGE_URI", "memory://")
    RATELIMIT_ENABLED = _as_bool(os.environ.get("RATELIMIT_ENABLED"), True)
    # Optional OpenAI-compatible AI tutor. Keep the API key server-side only.
    STUDY_AI_API_KEY = os.environ.get("STUDY_AI_API_KEY", "").strip()
    STUDY_AI_BASE_URL = os.environ.get("STUDY_AI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    STUDY_AI_MODEL = os.environ.get("STUDY_AI_MODEL", "gpt-4o-mini").strip()
    STUDY_AI_TIMEOUT_SECONDS = int(os.environ.get("STUDY_AI_TIMEOUT_SECONDS", "25"))


class TestConfig(Config):
    APP_ENV = "testing"
    TESTING = True
    WTF_CSRF_ENABLED = False
    SECRET_KEY = "test-secret-key"
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    AUTO_CREATE_DB = True
    SESSION_COOKIE_SECURE = False
    RATELIMIT_ENABLED = False
