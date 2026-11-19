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
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql.elements import conv

from src.models.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from src.models.code_file import CodeFile
    from src.models.task import Task

MAX_UPLOAD_SIZE_BYTES = 10485760  # 10 MiB


class UploadedCode(UUIDPrimaryKeyMixin, Base):
    """Analysis summary of the code uploaded for one task (exactly one per task).

    The migration has no updated_at column here, so TimestampMixin is not used.
    """

    __tablename__ = "uploaded_code"
    __table_args__ = (
        # Names match the migration; its unnamed constraints get PostgreSQL's default names.
        UniqueConstraint("task_id", name=conv("uploaded_code_task_id_key")),
        CheckConstraint(
            "complexity_level IN ('beginner', 'intermediate', 'advanced')",
            name=conv("uploaded_code_complexity_level_check"),
        ),
        CheckConstraint(
            f"upload_size_bytes <= {MAX_UPLOAD_SIZE_BYTES}", name=conv("valid_upload_size")
        ),
        Index("idx_uploaded_code_task_id", "task_id"),
    )

    COMPLEXITY_LEVELS: ClassVar[tuple[str, ...]] = ("beginner", "intermediate", "advanced")
    MAX_UPLOAD_SIZE_BYTES: ClassVar[int] = MAX_UPLOAD_SIZE_BYTES

    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False
    )
    detected_language: Mapped[str | None] = mapped_column(String(50))
    complexity_level: Mapped[str | None] = mapped_column(String(20))
    total_lines: Mapped[int | None] = mapped_column(Integer)
    total_files: Mapped[int | None] = mapped_column(Integer)
    upload_size_bytes: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    task: Mapped["Task"] = relationship(back_populates="uploaded_code")
    code_files: Mapped[list["CodeFile"]] = relationship(
        back_populates="uploaded_code", passive_deletes=True
    )

    def __repr__(self) -> str:
        return (
            f"UploadedCode(id={self.id!r}, task_id={self.task_id!r}, "
            f"detected_language={self.detected_language!r})"
        )
