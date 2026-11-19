"""Celery task that generates a learning document in the background (T094).

The API process only enqueues (DocumentQueueService, T095); the work happens here:
DocumentGenerationService.generate_document(task_id) (T093) does the Gemini calls and keeps the
row's status. This wrapper adds what a worker needs on top:
- Time budget (FR-025, 3 minutes): soft limit 170s raises SoftTimeLimitExceeded so the row can be
  saved as `failed` with a reason; the hard limit at 180s kills the child as a last resort.
  The budget is per attempt.
- Retries (max 3, delay 10/20/40s): only for errors another try can fix (database or connection
  trouble, retryable Gemini errors that outlived T093's own retries). Content problems, bad keys,
  deleted tasks and bugs fail at once. Between attempts the row goes back to `pending` so a
  poller keeps waiting instead of seeing a stale `failed`.
"""

import asyncio
import logging
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

from celery.exceptions import SoftTimeLimitExceeded  # type: ignore[import-untyped]
from sqlalchemy.exc import DBAPIError, InterfaceError, OperationalError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from src.db.config import get_database_url, to_async_url
from src.services.ai.gemini_client import GeminiClient, GeminiEmptyResponseError, GeminiError
from src.services.document.document_generation_service import (
    DocumentGenerationError,
    DocumentGenerationService,
)
from src.services.document.document_queue_service import DocumentQueueService
from src.tasks.celery_app import app

logger = logging.getLogger(__name__)

__all__ = ["generate_document_task", "retry_delay"]

SOFT_TIME_LIMIT_SECONDS = 170
HARD_TIME_LIMIT_SECONDS = 180
MAX_RETRIES = 3
RETRY_BASE_DELAY_SECONDS = 10

FAILED_MESSAGE = "문서 생성 중 오류가 발생했습니다. 잠시 후 다시 시도하세요."
TIMEOUT_MESSAGE = "문서 생성이 제한시간(3분)을 넘겨 중단되었습니다. 잠시 후 다시 시도하세요."


def retry_delay(retries_so_far: int) -> int:
    """Seconds before retry number `retries_so_far` + 1: 10, 20, 40."""
    return RETRY_BASE_DELAY_SECONDS << retries_so_far


def _is_transient(error: BaseException) -> bool:
    if isinstance(error, DBAPIError | InterfaceError | OperationalError | ConnectionError):
        return True
    if isinstance(error, DocumentGenerationError):
        cause = error.__cause__
        return isinstance(cause, GeminiError) and (
            cause.retryable or isinstance(cause, GeminiEmptyResponseError)
        )
    return False


async def _with_session(work: Callable[[AsyncSession], Awaitable[Any]]) -> Any:
    # A fresh engine per call: every task runs in its own event loop (asyncio.run), and pooled
    # asyncpg connections cannot be reused across loops.
    engine = create_async_engine(to_async_url(get_database_url()), poolclass=NullPool)
    try:
        async with async_sessionmaker(engine, expire_on_commit=False)() as session:
            return await work(session)
    finally:
        await engine.dispose()


async def _generate(task_id: uuid.UUID) -> None:
    async def work(session: AsyncSession) -> None:
        await DocumentGenerationService(GeminiClient(), session).generate_document(task_id)

    await _with_session(work)


async def _record_failure(task_id: uuid.UUID, reason: str) -> None:
    await _with_session(lambda session: DocumentQueueService(session).mark_failed(task_id, reason))


async def _record_retry(task_id: uuid.UUID) -> None:
    await _with_session(lambda session: DocumentQueueService(session).mark_pending(task_id))


@app.task(  # type: ignore[misc]  # celery ships no type information
    bind=True,
    name="documents.generate",
    queue="document_generation",
    soft_time_limit=SOFT_TIME_LIMIT_SECONDS,
    time_limit=HARD_TIME_LIMIT_SECONDS,
    max_retries=MAX_RETRIES,
)
def generate_document_task(self: Any, task_id: str) -> None:
    target = uuid.UUID(task_id)
    try:
        asyncio.run(_generate(target))
    except SoftTimeLimitExceeded:
        logger.error("문서 생성 제한시간 초과 task_id=%s", task_id)
        asyncio.run(_record_failure(target, TIMEOUT_MESSAGE))
        raise
    except Exception as error:
        if _is_transient(error) and self.request.retries < self.max_retries:
            delay = retry_delay(self.request.retries)
            logger.warning(
                "문서 생성 재시도 %d/%d (%ds 뒤) task_id=%s: %s",
                self.request.retries + 1,
                self.max_retries,
                delay,
                task_id,
                error,
            )
            asyncio.run(_record_retry(target))
            raise self.retry(exc=error, countdown=delay) from error
        logger.exception("문서 생성 실패 task_id=%s", task_id)
        asyncio.run(_record_failure(target, FAILED_MESSAGE))
        raise
