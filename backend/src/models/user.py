from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql.elements import conv

from src.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from src.models.project import Project
    from src.models.refresh_token import RefreshToken

EMAIL_PATTERN = r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$"


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(f"email ~* '{EMAIL_PATTERN}'", name=conv("valid_email")),
        Index("idx_users_email", "email"),
    )

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    skill_level: Mapped[str | None] = mapped_column(
        String(50), server_default=text("'Complete Beginner'")
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        back_populates="user", passive_deletes=True
    )
    projects: Mapped[list["Project"]] = relationship(back_populates="user", passive_deletes=True)

    def __repr__(self) -> str:
        return f"User(id={self.id!r}, email={self.email!r})"
