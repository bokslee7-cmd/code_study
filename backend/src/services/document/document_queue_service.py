"""Queue + status tracking for document generation (T095).

One LearningDocument row per task doubles as the queue entry: `pending` + a `celery_task_id`
means "queued", `in_progress` means a worker is generating (T093 sets it), `completed`/`failed`
are final. `enqueue` is idempotent while a run is queued or running, so a double click or a
retried request never starts two generations (T093 does not guard against that itself).

Like DocumentGenerationService this commits itself: the worker must be able to see the task and
the row the moment the message is dispatched, and a poller must see `pending` right away.
"""

import asyncio
import logging
import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.exceptions import AppError
from src.models import LearningDocument
from src.models.learning_document import CHAPTER_KEYS

logger = logging.getLogger(__name__)

__all__ = [
    "DISPATCH_FAILED_MESSAGE",
    "DocumentQueueService",
    "estimate_remaining_seconds",
    "failed_chapters",
]

DOCUMENT_QUEUE = "document_generation"
ESTIMATED_TOTAL_SECONDS = 180  # FR-025: a typical task completes within 3 minutes
# A run that started this long ago is dead (hard time limit is 180s), so it no longer blocks.
STALE_IN_PROGRESS = timedelta(seconds=ESTIMATED_TOTAL_SECONDS + 120)
MAX_ERROR_LENGTH = 2000
FAILED_CHAPTER_MARKER = "generation_failed"

DISPATCH_FAILED_MESSAGE = "문서 생성 작업을 대기열에 등록하지 못했습니다. 잠시 후 다시 시도하세요."
ALREADY_ACTIVE_MESSAGE = "이미 문서를 생성하고 있습니다. 완료될 때까지 기다려 주세요."

Dispatcher = Callable[[uuid.UUID, str], None]


def _dispatch_to_celery(task_id: uuid.UUID, celery_task_id: str) -> None:
    # Imported lazily: src.tasks.celery_app needs REDIS_URL at import time, and the API process
    # must still start (and uploads still work) without it.
    from src.tasks.document_generation import generate_document_task

    generate_document_task.apply_async(
        args=[str(task_id)],
        task_id=celery_task_id,
        queue=DOCUMENT_QUEUE,
        retry_policy={"max_retries": 1, "interval_start": 0.2, "interval_max": 1},
    )


def failed_chapters(content: dict[str, Any]) -> list[str]:
    """Chapters the generator gave up on (`{"generation_failed": true}`), in chapter order."""
    return [
        key
        for key in CHAPTER_KEYS
        if isinstance(content.get(key), dict) and content[key].get(FAILED_CHAPTER_MARKER) is True
    ]


def estimate_remaining_seconds(
    document: LearningDocument, *, now: datetime | None = None
) -> int | None:
    """Seconds left of the 180s budget, only while in progress (never below 0)."""
    started = document.generation_started_at
    if document.generation_status != LearningDocument.IN_PROGRESS or started is None:
        return None
    elapsed = ((now or datetime.now(UTC)) - started).total_seconds()
    return max(0, int(ESTIMATED_TOTAL_SECONDS - elapsed))


class DocumentQueueService:
    def __init__(self, session: AsyncSession, dispatch: Dispatcher | None = None) -> None:
        self._session = session
        self._dispatch = dispatch or _dispatch_to_celery

    async def enqueue(self, task_id: uuid.UUID) -> LearningDocument:
        """Queue a generation unless one is already queued or running (then a no-op).

        Never raises because the queue is down: the row becomes `failed` with a readable reason,
        so the upload that triggered this still succeeds and the user can request it again.
        """
        document, active = await self._lock_or_create(task_id)
        if active:
            return document
        return await self._start(document)

    async def regenerate(self, task_id: uuid.UUID) -> LearningDocument:
        """Start a new generation for a finished document; 409 while one is queued or running."""
        document, active = await self._lock_or_create(task_id)
        if active:
            raise AppError(
                409,
                "conflict",
                ALREADY_ACTIVE_MESSAGE,
                details={"task_id": str(task_id)},
            )
        return await self._start(document)

    async def get_document(self, task_id: uuid.UUID) -> LearningDocument | None:
        return await self._find(task_id)

    async def mark_failed(self, task_id: uuid.UUID, reason: str) -> None:
        """Record a failure the generation service could not (worker crash, time limit).

        A row already `failed` keeps its reason: the service saved a more specific one.
        """
        document = await self._find(task_id)
        if document is None or document.generation_status == LearningDocument.FAILED:
            return
        self._fail(document, reason)
        await self._session.commit()

    async def mark_pending(self, task_id: uuid.UUID) -> None:
        """Back to `pending` while Celery retries, so pollers keep waiting instead of giving up."""
        document = await self._find(task_id)
        if document is None:
            return
        self._reset(document)
        await self._session.commit()

    # ---- internals ----------------------------------------------------------------------

    async def _find(self, task_id: uuid.UUID, *, lock: bool = False) -> LearningDocument | None:
        query = select(LearningDocument).where(LearningDocument.task_id == task_id)
        if lock:
            query = query.with_for_update()
        return (await self._session.execute(query)).scalar_one_or_none()

    async def _lock_or_create(self, task_id: uuid.UUID) -> tuple[LearningDocument, bool]:
        document = await self._find(task_id, lock=True)
        if document is None:
            document = LearningDocument(
                task_id=task_id,
                content={key: {} for key in CHAPTER_KEYS},
                generation_status=LearningDocument.PENDING,
            )
            self._session.add(document)
            await self._session.flush()
            return document, False
        return document, self._is_active(document)

    @staticmethod
    def _is_active(document: LearningDocument) -> bool:
        if document.generation_status == LearningDocument.PENDING:
            return document.celery_task_id is not None
        if document.generation_status != LearningDocument.IN_PROGRESS:
            return False
        started = document.generation_started_at
        return started is None or datetime.now(UTC) - started < STALE_IN_PROGRESS

    @staticmethod
    def _reset(document: LearningDocument) -> None:
        document.generation_status = LearningDocument.PENDING
        document.generation_error = None
        document.generation_started_at = None
        document.generation_completed_at = None

    @staticmethod
    def _fail(document: LearningDocument, reason: str) -> None:
        document.generation_status = LearningDocument.FAILED
        document.generation_error = reason[:MAX_ERROR_LENGTH]
        document.generation_completed_at = datetime.now(UTC)

    async def _start(self, document: LearningDocument) -> LearningDocument:
        celery_task_id = str(uuid.uuid4())
        self._reset(document)
        document.celery_task_id = celery_task_id  # stored first: the worker may start instantly
        await self._session.commit()
        try:
            # apply_async talks to Redis synchronously; keep it off the event loop.
            await asyncio.to_thread(self._dispatch, document.task_id, celery_task_id)
        except Exception:
            logger.exception("문서 생성 작업 등록 실패 task_id=%s", document.task_id)
            self._fail(document, DISPATCH_FAILED_MESSAGE)
            await self._session.commit()
        return document
