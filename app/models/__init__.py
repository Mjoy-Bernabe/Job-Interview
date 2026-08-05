"""Model layer.

Entities represent application data, while repository classes isolate SQL and
other persistence operations from controllers.
"""
from .entities import Applicant, User
from .repositories import UserRepository, DashboardRepository

__all__ = ["User", "Applicant", "UserRepository", "DashboardRepository"]
