"""Repository interfaces (ports) - Define contracts for data access."""

from .content_repository import ContentRepository
from .job_repository import JobRepository
from .user_repository import UserRepository

__all__ = ["ContentRepository", "JobRepository", "UserRepository"]

