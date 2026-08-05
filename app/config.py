import os
from dotenv import load_dotenv

load_dotenv()


def get_int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


class Config:
    SECRET_KEY = os.getenv(
        "SECRET_KEY",
        "development-secret-key"
    )

    MYSQL_HOST = os.getenv(
        "MYSQL_HOST",
        "127.0.0.1"
    )

    MYSQL_PORT = get_int_env(
        "MYSQL_PORT",
        3306
    )

    MYSQL_USER = os.getenv(
        "MYSQL_USER",
        "root"
    )

    MYSQL_PASSWORD = os.getenv(
        "MYSQL_PASSWORD",
        ""
    )

    MYSQL_DB = os.getenv(
        "MYSQL_DB",
        "auth_db"
    )

    MYSQL_CURSORCLASS = "DictCursor"

    MYSQL_CUSTOM_OPTIONS = {
        "ssl": {
            "ssl_mode": os.getenv(
                "MYSQL_SSL_MODE",
                "REQUIRED"
            )
        }
    }

    MAX_RESUME_SIZE = get_int_env(
        "MAX_RESUME_SIZE",
        10 * 1024 * 1024
    )