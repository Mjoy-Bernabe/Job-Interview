"""Reusable database repositories for the MVC model layer.

Controllers should call these classes instead of embedding new SQL directly.
Existing legacy routes remain compatible and can be migrated incrementally.
"""
from typing import Any, Optional

from app.extensions import mysql


class BaseRepository:
    """Small helper for safe cursor lifecycle management."""

    @staticmethod
    def fetch_one(query: str, params: tuple = ()) -> Optional[tuple]:
        cursor = mysql.connection.cursor()
        try:
            cursor.execute(query, params)
            return cursor.fetchone()
        finally:
            cursor.close()

    @staticmethod
    def fetch_all(query: str, params: tuple = ()) -> tuple:
        cursor = mysql.connection.cursor()
        try:
            cursor.execute(query, params)
            return cursor.fetchall()
        finally:
            cursor.close()

    @staticmethod
    def execute(query: str, params: tuple = ()) -> int:
        cursor = mysql.connection.cursor()
        try:
            cursor.execute(query, params)
            mysql.connection.commit()
            return cursor.rowcount
        except Exception:
            mysql.connection.rollback()
            raise
        finally:
            cursor.close()


class UserRepository(BaseRepository):
    """Database operations involving users."""

    @classmethod
    def find_by_id(cls, user_id: int) -> Optional[tuple]:
        return cls.fetch_one(
            "SELECT user_id, email, username, contact_num, user_type "
            "FROM users WHERE user_id = %s",
            (user_id,),
        )

    @classmethod
    def find_role(cls, user_id: int) -> Optional[str]:
        row = cls.fetch_one(
            "SELECT user_type FROM users WHERE user_id = %s", (user_id,)
        )
        return row[0] if row else None


class DashboardRepository(BaseRepository):
    """Aggregate values used by administrator dashboards."""

    @classmethod
    def admin_counts(cls) -> dict[str, int]:
        total = cls.fetch_one("SELECT COUNT(*) FROM users")[0]
        hr = cls.fetch_one("SELECT COUNT(*) FROM users WHERE user_type = 'HR'")[0]
        applicants = cls.fetch_one(
            "SELECT COUNT(*) FROM users WHERE user_type = 'Applicant'"
        )[0]
        return {
            "total_users": total or 0,
            "total_hr": hr or 0,
            "total_applicants": applicants or 0,
        }
