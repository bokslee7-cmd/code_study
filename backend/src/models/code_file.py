import uuid
from datetime import datetime
from typing import TYPE_CHECKING, ClassVar

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql.elements import conv

from src.models.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from src.models.uploaded_code import UploadedCode

SUPPORTED_EXTENSIONS = (
    ".py",
    ".js",
    ".ts",
    ".jsx",
    ".tsx",
    ".html",
    ".css",
    ".java",
    ".cpp",
    ".c",
    ".txt",
    ".md",
)
_EXTENSION_SQL_LIST = ", ".join(f"'{extension}'" for extension in SUPPORTED_EXTENSIONS)


class CodeFile(UUIDPrimaryKeyMixin, Base):
    """Metadata of one uploaded source file; the file itself lives under storage_path.

    The migration has no updated_at column here, so TimestampMixin is not used.
    """

    __tablename__ = "code_files"
    __table_args__ = (
        CheckConstraint(
            f"file_extension IN ({_EXTENSION_SQL_LIST})", name=conv("supported_extension")
        ),
        Index("idx_code_files_uploaded_code_id", "uploaded_code_id"),
    )

    SUPPORTED_EXTENSIONS: ClassVar[tuple[str, ...]] = SUPPORTED_EXTENSIONS

    uploaded_code_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("uploaded_code.id", ondelete="CASCADE"), nullable=False
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    # Relative path inside an uploaded folder; null for single-file or pasted uploads.
    file_path: Mapped[str | None] = mapped_column(Text)
    file_extension: Mapped[str | None] = mapped_column(String(20))
    file_size_bytes: Mapped[int | None] = mapped_column(Integer)
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    uploaded_code: Mapped["UploadedCode"] = relationship(back_populates="code_files")

    def __repr__(self) -> str:
        return (
            f"CodeFile(id={self.id!r}, file_name={self.file_name!r}, "
            f"file_extension={self.file_extension!r})"
        )
