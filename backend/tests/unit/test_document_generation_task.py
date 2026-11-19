import importlib
import sys
import uuid
from collections.abc import Iterator
from typing import Any
from unittest.mock import AsyncMock

import pytest
from celery.exceptions import SoftTimeLimitExceeded  # type: ignore[import-untyped]
from sqlalchemy.exc import OperationalError
from src.api.exceptions import NotFoundException
from src.services.ai.gemini_client import (
    GeminiAPIError,
    GeminiConfigError,
    GeminiEmptyResponseError,
)
from src.services.document.document_generation_service import DocumentGenerationError

TASK_ID = uuid.uuid4()


@pytest.fixture
def module(monkeypatch: pytest.MonkeyPatch) -> Iterator[Any]:
    """Fresh import with the three DB/Gemini touch points replaced by async doubles."""
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/2")
    for name in ("src.tasks.celery_app", "src.tasks.document_generation"):
        sys.modules.pop(name, None)
    loaded = importlib.import_module("src.tasks.document_generation")
    monkeypatch.setattr(loaded, "_generate", AsyncMock())
    monkeypatch.setattr(loaded, "_record_failure", AsyncMock())
    monkeypatch.setattr(loaded, "_record_retry", AsyncMock())
    yield loaded
    for name in ("src.tasks.celery_app", "src.tasks.document_generation"):
        sys.modules.pop(name, None)


def _run(module: Any) -> Any:
    return module.generate_document_task.apply(args=[str(TASK_ID)])


def _caused_by(error: Exception) -> DocumentGenerationError:
    wrapped = DocumentGenerationError("Gemini 호출이 실패했습니다")
    wrapped.__cause__ = error
    return wrapped


def _db_error() -> OperationalError:
    return OperationalError("SELECT 1", {}, Exception("connection reset"))


# ---------------------------------------------------------------- registration


def test_task_is_registered_on_the_document_queue_with_the_three_minute_limit(module: Any):
    task = module.generate_document_task

    assert task.name == "documents.generate"
    assert task.queue == "document_generation"
    assert task.soft_time_limit == 170
    assert task.time_limit == 180  # FR-025: 3 minutes
    assert task.max_retries == 3


def test_celery_app_loads_the_task_module_when_a_worker_starts(module: Any):
    celery_app = sys.modules["src.tasks.celery_app"].app

    assert "src.tasks.document_generation" in celery_app.conf.include


# ---------------------------------------------------------------- happy path


def test_task_generates_the_document_of_the_given_task(module: Any):
    result = _run(module)

    assert result.successful()
    module._generate.assert_awaited_once_with(TASK_ID)
    module._record_failure.assert_not_awaited()
    module._record_retry.assert_not_awaited()


# ---------------------------------------------------------------- transient errors retry


@pytest.mark.parametrize(
    "error",
    [
        _db_error(),
        ConnectionError("redis"),
        _caused_by(GeminiAPIError("503", retryable=True)),
        _caused_by(GeminiEmptyResponseError("빈 응답")),
    ],
    ids=["db", "connection", "gemini-retryable", "gemini-empty"],
)
def test_transient_error_is_retried_and_the_status_goes_back_to_pending(module: Any, error: Any):
    module._generate.side_effect = [error, None]

    result = _run(module)

    assert result.successful()
    assert module._generate.await_count == 2
    module._record_retry.assert_awaited_once_with(TASK_ID)
    module._record_failure.assert_not_awaited()


def test_retries_stop_after_three_and_the_failure_is_recorded(module: Any):
    module._generate.side_effect = _db_error()

    result = _run(module)

    assert result.failed()
    assert module._generate.await_count == 4  # first run + 3 retries
    assert module._record_retry.await_count == 3
    module._record_failure.assert_awaited_once()
    assert module._record_failure.await_args.args[0] == TASK_ID


def test_retry_delay_grows_exponentially(module: Any):
    assert [module.retry_delay(n) for n in range(3)] == [10, 20, 40]


# ---------------------------------------------------------------- permanent errors do not retry


@pytest.mark.parametrize(
    "error",
    [
        DocumentGenerationError("유효한 챕터가 부족합니다"),
        _caused_by(GeminiAPIError("401", retryable=False)),
        _caused_by(GeminiConfigError("키 없음")),
        NotFoundException("태스크 없음"),
        ValueError("bug"),
    ],
    ids=["content", "gemini-fatal", "gemini-config", "task-gone", "bug"],
)
def test_permanent_error_is_recorded_without_retrying(module: Any, error: Exception):
    module._generate.side_effect = error

    result = _run(module)

    assert result.failed()
    module._generate.assert_awaited_once()
    module._record_retry.assert_not_awaited()
    module._record_failure.assert_awaited_once()


def test_failure_reason_is_a_readable_korean_message(module: Any):
    module._generate.side_effect = ValueError("secret internals")

    _run(module)

    reason = module._record_failure.await_args.args[1]
    assert "문서 생성" in reason
    assert "secret internals" not in reason  # no internals in what the user may see


# ---------------------------------------------------------------- time limit


def test_soft_time_limit_marks_the_document_failed_with_a_timeout_reason(module: Any):
    module._generate.side_effect = SoftTimeLimitExceeded()

    result = _run(module)

    assert result.failed()
    module._generate.assert_awaited_once()
    module._record_retry.assert_not_awaited()
    reason = module._record_failure.await_args.args[1]
    assert "3분" in reason
