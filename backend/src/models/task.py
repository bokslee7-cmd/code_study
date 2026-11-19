import uuid
from datetime import datetime
from typing import TYPE_CHECKING, ClassVar

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql.elements import conv

from src.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from src.models.learning_document import LearningDocument
    from src.models.project import Project
    from src.models.uploaded_code import UploadedCode


class Task(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One study unit inside a project. Deleted tasks are only marked (soft delete)."""

    __tablename__ = "tasks"
    __table_args__ = (
        # Names match the migration; the two unnamed checks there get PostgreSQL's default names.
        CheckConstraint("char_length(title) >= 5", name=conv("title_min_length")),
        CheckConstraint("char_length(description) <= 500", name=conv("description_max_length")),
        CheckConstraint(
            "upload_method IN ('file', 'folder', 'paste')",
            name=conv("tasks_upload_method_check"),
        ),
        CheckConstraint(
            "deletion_status IN ('active', 'trashed')",
            name=conv("tasks_deletion_status_check"),
        ),
        UniqueConstraint("project_id", "task_number", name="unique_task_number_per_project"),
        Index("idx_tasks_project_id", "project_id"),
        Index("idx_tasks_deletion_status", "deletion_status"),
        Index(
            "idx_tasks_project_active",
            "project_id",
            "deletion_status",
            postgresql_where=text("deletion_status = 'active'"),
        ),
        Index("idx_tasks_number_order", "project_id", "task_number"),
    )

    ACTIVE: ClassVar[str] = "active"
    TRASHED: ClassVar[str] = "trashed"
    UPLOAD_METHODS: ClassVar[tuple[str, ...]] = ("file", "folder", "paste")

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    # Sequential per project (1, 2, 3...); the service (T068) assigns the next number.
    task_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    upload_method: Mapped[str | None] = mapped_column(String(20))
    deletion_status: Mapped[str] = mapped_column(
        String(20), default=ACTIVE, server_default=text("'active'"), nullable=False
    )
    trashed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # trashed_at + 30 days; the cleanup job (T172) deletes tasks past this moment.
    scheduled_deletion_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    project: Mapped["Project"] = relationship(back_populates="tasks")
    uploaded_code: Mapped["UploadedCode | None"] = relationship(
        back_populates="task", uselist=False, passive_deletes=True
    )
    learning_document: Mapped["LearningDocument | None"] = relationship(
        back_populates="task", uselist=False, passive_deletes=True
    )

    def __repr__(self) -> str:
        return (
            f"Task(id={self.id!r}, task_number={self.task_number!r}, title={self.title!r}, "
            f"deletion_status={self.deletion_status!r})"
        )
