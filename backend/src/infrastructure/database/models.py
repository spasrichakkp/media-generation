"""SQLAlchemy ORM models mapping to domain entities."""

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func


class Base(AsyncAttrs, DeclarativeBase):
    """
    Base class for all ORM models.
    
    Uses AsyncAttrs mixin to enable async attribute access.
    """
    pass


class UserModel(Base):
    """
    ORM model for User entity.
    
    Maps to 'users' table in the database.
    """
    __tablename__ = "users"
    
    # Primary key
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        index=True
    )
    
    # Required fields
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    
    # Optional fields
    api_key_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        onupdate=func.now(),
        nullable=True
    )
    
    # Status flags
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Quota management
    quota_limit: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    quota_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    quota_reset_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    
    # Relationships
    jobs: Mapped[list["GenerationJobModel"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    
    def __repr__(self) -> str:
        return f"<UserModel(id={self.id}, username={self.username}, email={self.email})>"


class GenerationJobModel(Base):
    """
    ORM model for GenerationJob entity.
    
    Maps to 'generation_jobs' table in the database.
    Partitioned by created_at for performance.
    """
    __tablename__ = "generation_jobs"
    
    # Primary key
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        index=True
    )
    
    # Foreign keys
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Required fields
    content_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    
    # Optional fields
    model_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    parameters: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False, index=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        onupdate=func.now(),
        nullable=True
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True
    )
    
    # Error handling
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Webhook
    webhook_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Result
    result_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    user: Mapped["UserModel"] = relationship(back_populates="jobs", lazy="selectin")
    content: Mapped[Optional["GeneratedContentModel"]] = relationship(
        back_populates="job",
        cascade="all, delete-orphan",
        lazy="selectin",
        uselist=False
    )
    
    # Indexes for common queries
    __table_args__ = (
        Index("ix_jobs_user_status", "user_id", "status"),
        Index("ix_jobs_status_priority", "status", "priority", "created_at"),
        Index("ix_jobs_created_at_status", "created_at", "status"),
    )
    
    def __repr__(self) -> str:
        return (
            f"<GenerationJobModel(id={self.id}, user_id={self.user_id}, "
            f"status={self.status}, content_type={self.content_type})>"
        )


class GeneratedContentModel(Base):
    """
    ORM model for GeneratedContent entity.
    
    Maps to 'generated_content' table in the database.
    """
    __tablename__ = "generated_content"
    
    # Primary key
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        index=True
    )
    
    # Foreign keys
    job_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("generation_jobs.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )
    
    # Required fields
    content_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    content_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    
    # Optional fields
    file_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    file_format: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    width: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    height: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    duration: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    content_metadata: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True
    )
    
    # Access control
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    
    # Content moderation
    nsfw_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    is_moderated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    
    # Relationships
    job: Mapped["GenerationJobModel"] = relationship(back_populates="content", lazy="selectin")
    
    # Indexes for common queries
    __table_args__ = (
        Index("ix_content_type_public", "content_type", "is_public"),
        Index("ix_content_nsfw", "nsfw_score"),
        Index("ix_content_moderated", "is_moderated"),
    )
    
    def __repr__(self) -> str:
        return (
            f"<GeneratedContentModel(id={self.id}, job_id={self.job_id}, "
            f"content_type={self.content_type})>"
        )

