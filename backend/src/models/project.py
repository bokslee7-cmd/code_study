import uuid
from datetime import datetime
from typing import TYPE_CHECKING, ClassVar

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql.elements import conv

from src.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from src.models.task import Task
    from src.models.user import User


class Project(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A learning container for related tasks. Deleted projects are only marked (soft delete)."""

    __tablename__ = "projects"
    __table_args__ = (
        # Names match the migration: title_min_length is named there, the status check is
        # unnamed there so PostgreSQL generates projects_deletion_status_check.
        CheckConstraint("char_length(title) >= 1", name=conv("title_min_length")),
        CheckConstraint(
            "deletion_status IN ('active', 'trashed')",
            name=conv("projects_deletion_status_check"),
        ),
        Index("idx_projects_user_id", "user_id"),
        Index("idx_projects_deletion_status", "deletion_status"),
        Index(
            "idx_projects_user_active",
            "user_id",
            "deletion_status",
            postgresql_where=text("deletion_status = 'active'"),
        ),
    )

    ACTIVE: ClassVar[str] = "active"
    TRASHED: ClassVar[str] = "trashed"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    # Last task activity; bumped by the services when tasks change (T068).
    last_activity_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    deletion_status: Mapped[str] = mapped_column(
        String(20), default=ACTIVE, server_default=text("'active'"), nullable=False
    )
    trashed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # trashed_at + 30 days; the cleanup job (T172) deletes projects past this moment.
    scheduled_deletion_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped["User"] = relationship(back_populates="projects")
    tasks: Mapped[list["Task"]] = relationship(back_populates="project", passive_deletes=True)

    def __repr__(self) -> str:
        return (
            f"Project(id={self.id!r}, title={self.title!r}, "
            f"deletion_status={self.deletion_status!r})"
        )
