"""Application configuration loaded from environment variables."""
import os

from dotenv import load_dotenv

# Load local MySQL credentials from .env before Config is created.
load_dotenv()


def get_int_env(name: str, default: int) -> int:
    """Read an integer environment variable without crashing on bad input."""
    raw_value = os.environ.get(name)
    if raw_value is None or not raw_value.strip():
        return default

    try:
        return int(raw_value.strip())
    except ValueError:
        return default


def get_bool_env(name: str, default: bool) -> bool:
    raw_value = os.environ.get(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "change-this-secret-in-render")

    MYSQL_HOST = os.environ.get("MYSQL_HOST", "localhost")
    MYSQL_USER = os.environ.get("MYSQL_USER", "root")
    MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "")
    MYSQL_DB = os.environ.get("MYSQL_DB", "auth_db")
    MYSQL_PORT = get_int_env("MYSQL_PORT", 3306)

    UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", "uploads")
    PROFILE_UPLOAD_FOLDER = os.environ.get(
        "PROFILE_UPLOAD_FOLDER", "static/uploads"
    )
    ALLOWED_RESUME_EXTENSIONS = {"pdf", "doc", "docx"}
    ALLOWED_PROFILE_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}
    MAX_RESUME_SIZE = get_int_env("MAX_RESUME_SIZE", 10 * 1024 * 1024)
    MAX_CONTENT_LENGTH = MAX_RESUME_SIZE

    RESUME_ELIGIBLE_LABELS = {"Strong Fit", "Moderate Fit"}

    MAIL_SERVER = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = get_int_env("MAIL_PORT", 587)
    MAIL_USE_TLS = get_bool_env("MAIL_USE_TLS", True)
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME", "")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", "")

    RATELIMIT_DEFAULT = os.environ.get("RATELIMIT_DEFAULT", "10 per minute")
    RATELIMIT_STORAGE_URI = os.environ.get("RATELIMIT_STORAGE_URI", "memory://")

    SUMMARY_REPORT_DIR = os.environ.get(
        "SUMMARY_REPORT_DIR", "summary_reports"
    )
