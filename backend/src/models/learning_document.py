import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, ClassVar

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql.elements import conv

from src.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from src.models.task import Task

CHAPTER_KEYS = tuple(f"chapter{n}" for n in range(1, 8))
_STRUCTURE_CHECK = "jsonb_typeof(content) = 'object' AND " + " AND ".join(
    f"content ? '{key}'" for key in CHAPTER_KEYS
)


class LearningDocument(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """AI-generated 7-chapter learning document for one task (exactly one per task).

    The content column must already contain chapter1..chapter7 keys when the row is inserted,
    so a pending row needs a skeleton such as {"chapter1": {}, ..., "chapter7": {}}.
    The shape inside each chapter is not checked by the database.
    """

    __tablename__ = "learning_documents"
    __table_args__ = (
        # Names match the migration; its unnamed constraints get PostgreSQL's default names.
        UniqueConstraint("task_id", name=conv("learning_documents_task_id_key")),
        CheckConstraint(
            "generation_status IN ('pending', 'in_progress', 'completed', 'failed')",
            name=conv("learning_documents_generation_status_check"),
        ),
        CheckConstraint(_STRUCTURE_CHECK, name=conv("valid_content_structure")),
        Index("idx_learning_documents_task_id", "task_id"),
        Index("idx_learning_documents_status", "generation_status"),
        Index("idx_learning_documents_celery_task", "celery_task_id"),
    )

    PENDING: ClassVar[str] = "pending"
    IN_PROGRESS: ClassVar[str] = "in_progress"
    COMPLETED: ClassVar[str] = "completed"
    FAILED: ClassVar[str] = "failed"
    STATUSES: ClassVar[tuple[str, ...]] = (PENDING, IN_PROGRESS, COMPLETED, FAILED)
    CHAPTER_KEYS: ClassVar[tuple[str, ...]] = CHAPTER_KEYS

    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False
    )
    content: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    # The migration only has DEFAULT 'pending' (no NOT NULL), so the column stays nullable.
    generation_status: Mapped[str | None] = mapped_column(
        String(20), server_default=text("'pending'")
    )
    generation_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    generation_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    generation_error: Mapped[str | None] = mapped_column(Text)
    celery_task_id: Mapped[str | None] = mapped_column(String(255))

    task: Mapped["Task"] = relationship(back_populates="learning_document")

    def __repr__(self) -> str:
        return (
            f"LearningDocument(id={self.id!r}, task_id={self.task_id!r}, "
            f"generation_status={self.generation_status!r})"
        )
