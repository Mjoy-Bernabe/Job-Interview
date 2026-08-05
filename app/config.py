"""Application configuration loaded from environment variables.

The database configuration supports three deployment styles:
1. Railway public URL copied into MYSQL_PUBLIC_URL or DATABASE_URL.
2. Railway public TCP proxy variables copied individually.
3. Standard MYSQL_HOST/MYSQL_PORT/MYSQL_USER/MYSQL_PASSWORD/MYSQL_DB values.
"""
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


def _usable_database_url() -> str | None:
    """Return a resolved public database URL, ignoring unresolved placeholders."""
    for variable_name in ("MYSQL_PUBLIC_URL", "DATABASE_URL", "MYSQL_URL"):
        value = os.environ.get(variable_name, "").strip()
        if value and "${" not in value:
            return value
    return None


def _database_settings() -> dict[str, object]:
    """Resolve MySQL settings from a URL, Railway variables, or normal variables."""
    database_url = _usable_database_url()

    if database_url:
        parsed = urlparse(database_url)
        if parsed.scheme not in {"mysql", "mysql+pymysql", "mysql+mysqldb"}:
            raise ValueError(
                "MYSQL_PUBLIC_URL/DATABASE_URL must start with mysql://"
            )

        return {
            "host": parsed.hostname or "127.0.0.1",
            "port": parsed.port or 3306,
            "user": unquote(parsed.username or "root"),
            "password": unquote(parsed.password or ""),
            "database": unquote(parsed.path.lstrip("/") or "railway"),
            "source": "public database URL",
        }

    # These names are produced by Railway after Public Networking is enabled.
    railway_public_host = os.environ.get(
        "RAILWAY_TCP_PROXY_DOMAIN", ""
    ).strip()
    railway_public_port = os.environ.get(
        "RAILWAY_TCP_PROXY_PORT", ""
    ).strip()

    if railway_public_host and railway_public_port:
        try:
            port = int(railway_public_port)
        except ValueError:
            port = 3306

        return {
            "host": railway_public_host,
            "port": port,
            "user": os.environ.get(
                "MYSQLUSER", os.environ.get("MYSQL_USER", "root")
            ),
            "password": os.environ.get(
                "MYSQLPASSWORD", os.environ.get("MYSQL_PASSWORD", "")
            ),
            "database": os.environ.get(
                "MYSQLDATABASE",
                os.environ.get("MYSQL_DATABASE", os.environ.get("MYSQL_DB", "railway")),
            ),
            "source": "Railway public TCP proxy variables",
        }

    return {
        "host": os.environ.get(
            "MYSQL_HOST", os.environ.get("MYSQLHOST", "127.0.0.1")
        ),
        "port": get_int_env(
            "MYSQL_PORT", get_int_env("MYSQLPORT", 3306)
        ),
        "user": os.environ.get(
            "MYSQL_USER", os.environ.get("MYSQLUSER", "root")
        ),
        "password": os.environ.get(
            "MYSQL_PASSWORD", os.environ.get("MYSQLPASSWORD", "")
        ),
        "database": os.environ.get(
            "MYSQL_DB",
            os.environ.get(
                "MYSQL_DATABASE", os.environ.get("MYSQLDATABASE", "auth_db")
            ),
        ),
        "source": "individual MySQL variables",
    }


DB_SETTINGS = _database_settings()


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "thesis1")

    MYSQL_HOST = str(DB_SETTINGS["host"])
    MYSQL_PORT = int(DB_SETTINGS["port"])
    MYSQL_USER = str(DB_SETTINGS["user"])
    MYSQL_PASSWORD = str(DB_SETTINGS["password"])
    MYSQL_DB = str(DB_SETTINGS["database"])
    MYSQL_CONNECTION_SOURCE = str(DB_SETTINGS["source"])

    # Keep Unicode handling predictable for imported resume and applicant data.
    MYSQL_CURSORCLASS = "Cursor"

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
