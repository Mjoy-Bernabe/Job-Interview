"""Application configuration for local MySQL and Aiven MySQL on Render."""
from __future__ import annotations

import os
from urllib.parse import unquote, urlparse

from dotenv import load_dotenv

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


def _resolved_database_url() -> str | None:
    """Return a fully resolved MySQL URL, ignoring placeholder values."""
    for variable_name in ("MYSQL_PUBLIC_URL", "DATABASE_URL", "MYSQL_URL"):
        value = os.environ.get(variable_name, "").strip()
        if value and "${" not in value:
            return value
    return None


def _database_settings() -> dict[str, object]:
    """Resolve DB settings.

    Explicit MYSQL_* variables are intentionally preferred. This prevents an
    old Railway DATABASE_URL or MYSQL_PUBLIC_URL from overriding new Aiven
    credentials configured in Render.
    """
    explicit_host = os.environ.get("MYSQL_HOST", "").strip()
    if explicit_host:
        return {
            "host": explicit_host,
            "port": get_int_env("MYSQL_PORT", 3306),
            "user": os.environ.get("MYSQL_USER", "root"),
            "password": os.environ.get("MYSQL_PASSWORD", ""),
            "database": os.environ.get("MYSQL_DB", "auth_db"),
            "source": "explicit MYSQL_* variables",
        }

    database_url = _resolved_database_url()
    if database_url:
        parsed = urlparse(database_url)
        if parsed.scheme not in {"mysql", "mysql+pymysql", "mysql+mysqldb"}:
            raise ValueError("Database URL must start with mysql://")
        return {
            "host": parsed.hostname or "127.0.0.1",
            "port": parsed.port or 3306,
            "user": unquote(parsed.username or "root"),
            "password": unquote(parsed.password or ""),
            "database": unquote(parsed.path.lstrip("/") or "auth_db"),
            "source": "database URL",
        }

    return {
        "host": os.environ.get("MYSQLHOST", "127.0.0.1"),
        "port": get_int_env("MYSQLPORT", 3306),
        "user": os.environ.get("MYSQLUSER", "root"),
        "password": os.environ.get("MYSQLPASSWORD", ""),
        "database": os.environ.get("MYSQLDATABASE", "auth_db"),
        "source": "local/default MySQL variables",
    }


def _mysql_custom_options(host: str) -> dict[str, object]:
    """Build mysqlclient options for Aiven TLS or local MySQL.

    Render/Aiven: set MYSQL_SSL_MODE=REQUIRED. Optionally set MYSQL_SSL_CA to
    the path of Aiven's downloaded ca.pem when it is included in the project.
    Local Workbench/MySQL: leave MYSQL_SSL_MODE unset or set it to DISABLED.
    """
    configured_mode = os.environ.get("MYSQL_SSL_MODE", "").strip().upper()
    is_remote = host not in {"localhost", "127.0.0.1", "::1"}
    mode = configured_mode or ("REQUIRED" if is_remote else "DISABLED")

    if mode in {"", "DISABLED", "OFF", "FALSE", "0"}:
        return {}

    options: dict[str, object] = {
        "ssl_mode": mode,
        "connect_timeout": get_int_env("MYSQL_CONNECT_TIMEOUT", 20),
    }

    ca_path = os.environ.get("MYSQL_SSL_CA", "").strip()
    if ca_path:
        options["ssl"] = {"ca": ca_path}

    return options


DB_SETTINGS = _database_settings()


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "change-this-secret-in-render")

    MYSQL_HOST = str(DB_SETTINGS["host"])
    MYSQL_PORT = int(DB_SETTINGS["port"])
    MYSQL_USER = str(DB_SETTINGS["user"])
    MYSQL_PASSWORD = str(DB_SETTINGS["password"])
    MYSQL_DB = str(DB_SETTINGS["database"])
    MYSQL_CONNECTION_SOURCE = str(DB_SETTINGS["source"])
    MYSQL_CURSORCLASS = "Cursor"
    MYSQL_CUSTOM_OPTIONS = _mysql_custom_options(MYSQL_HOST)

    UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", "uploads")
    PROFILE_UPLOAD_FOLDER = os.environ.get("PROFILE_UPLOAD_FOLDER", "static/uploads")
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
    SUMMARY_REPORT_DIR = os.environ.get("SUMMARY_REPORT_DIR", "summary_reports")
