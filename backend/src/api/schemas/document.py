from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel

DocumentStatus = Literal["pending", "in_progress", "completed", "failed"]


class DocumentFile(BaseModel):
    """One uploaded file for the code panel (no storage path or database ids)."""

    path: str
    language: str
    content: str


class DocumentStatusResponse(BaseModel):
    """Cheap polling payload of GET /tasks/{id}/document/status."""

    task_id: UUID
    status: DocumentStatus
    generation_started_at: datetime | None
    generation_completed_at: datetime | None
    generation_error: str | None
    failed_chapters: list[str]
    estimated_remaining_seconds: int | None  # only while in_progress


class DocumentResponse(BaseModel):
    """GET /tasks/{id}/document: the chapters as stored (chapter1..chapter7) plus the code."""

    id: UUID
    task_id: UUID
    status: DocumentStatus
    content: dict[str, Any]
    failed_chapters: list[str]
    generation_error: str | None
    generation_started_at: datetime | None
    generation_completed_at: datetime | None
    files: list[DocumentFile]
