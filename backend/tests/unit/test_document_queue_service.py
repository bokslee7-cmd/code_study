import sys
import types
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from src.api.exceptions import AppError
from src.models import LearningDocument
from src.services.document.document_queue_service import (
    DISPATCH_FAILED_MESSAGE,
    DocumentQueueService,
    estimate_remaining_seconds,
    failed_chapters,
)

TASK_ID = uuid.uuid4()
NOW = datetime(2026, 11, 18, 12, 0, tzinfo=UTC)


def _document(status: str | None, **overrides: object) -> LearningDocument:
    values: dict[str, object] = {
        "id": uuid.uuid4(),
        "task_id": TASK_ID,
        "content": {key: {} for key in LearningDocument.CHAPTER_KEYS},
        "generation_status": status,
    }
    values.update(overrides)
    return LearningDocument(**values)


class _Harness:
    """Session double + dispatch double sharing one call log, so call order can be asserted."""

    def __init__(self, existing: LearningDocument | None = None) -> None:
        self.calls: list[str] = []
        self.session = MagicMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = existing
        self.session.execute = AsyncMock(return_value=result)
        self.session.add = MagicMock(side_effect=lambda _: self.calls.append("add"))
        self.session.flush = AsyncMock(side_effect=lambda: self.calls.append("flush"))
        self.session.commit = AsyncMock(side_effect=lambda: self.calls.append("commit"))
        self.dispatched: list[tuple[uuid.UUID, str]] = []
        self.fail_dispatch: Exception | None = None

        def dispatch(task_id: uuid.UUID, celery_task_id: str) -> None:
            self.calls.append("dispatch")
            if self.fail_dispatch:
                raise self.fail_dispatch
            self.dispatched.append((task_id, celery_task_id))

        self.service = DocumentQueueService(self.session, dispatch=dispatch)


# ---------------------------------------------------------------- enqueue


async def test_enqueue_creates_a_pending_row_and_commits_before_dispatching():
    harness = _Harness()

    document = await harness.service.enqueue(TASK_ID)

    assert document.task_id == TASK_ID
    assert document.generation_status == LearningDocument.PENDING
    assert set(document.content) == set(LearningDocument.CHAPTER_KEYS)
    # The worker must be able to see the committed task/row, so commit comes before dispatch.
    assert harness.calls.index("commit") < harness.calls.index("dispatch")
    [(task_id, celery_task_id)] = harness.dispatched
    assert task_id == TASK_ID
    assert document.celery_task_id == celery_task_id
    uuid.UUID(celery_task_id)  # a valid uuid string


async def test_enqueue_locks_the_row_to_stop_concurrent_duplicates():
    harness = _Harness()

    await harness.service.enqueue(TASK_ID)

    statement = harness.session.execute.call_args_list[0].args[0]
    assert "FOR UPDATE" in str(statement.compile())


@pytest.mark.parametrize(
    "existing",
    [
        _document(LearningDocument.IN_PROGRESS, generation_started_at=datetime.now(UTC)),
        _document(LearningDocument.PENDING, celery_task_id="already-queued"),
    ],
)
async def test_enqueue_does_nothing_when_generation_is_already_queued_or_running(
    existing: LearningDocument,
):
    harness = _Harness(existing)

    document = await harness.service.enqueue(TASK_ID)

    assert document is existing
    assert harness.dispatched == []
    assert existing.celery_task_id in (None, "already-queued")


async def test_enqueue_requeues_a_pending_row_that_never_got_a_celery_id():
    existing = _document(LearningDocument.PENDING)
    harness = _Harness(existing)

    await harness.service.enqueue(TASK_ID)

    assert len(harness.dispatched) == 1
    assert existing.celery_task_id == harness.dispatched[0][1]


async def test_enqueue_restarts_an_in_progress_row_whose_worker_died():
    stale = datetime.now(UTC) - timedelta(minutes=10)
    existing = _document(LearningDocument.IN_PROGRESS, generation_started_at=stale)
    harness = _Harness(existing)

    await harness.service.enqueue(TASK_ID)

    assert len(harness.dispatched) == 1
    assert existing.generation_status == LearningDocument.PENDING


@pytest.mark.parametrize("status", [LearningDocument.COMPLETED, LearningDocument.FAILED])
async def test_enqueue_restarts_a_finished_row_and_clears_the_old_outcome(status: str):
    existing = _document(
        status,
        celery_task_id="old",
        generation_error="예전 오류",
        generation_started_at=NOW,
        generation_completed_at=NOW,
    )
    harness = _Harness(existing)

    await harness.service.enqueue(TASK_ID)

    assert existing.generation_status == LearningDocument.PENDING
    assert existing.generation_error is None
    assert existing.generation_started_at is None
    assert existing.generation_completed_at is None
    assert existing.celery_task_id not in (None, "old")
    assert len(harness.dispatched) == 1


async def test_enqueue_marks_the_row_failed_when_the_queue_is_unreachable():
    harness = _Harness()
    harness.fail_dispatch = ConnectionError("redis down")

    document = await harness.service.enqueue(TASK_ID)  # the upload must not fail because of this

    assert document.generation_status == LearningDocument.FAILED
    assert document.generation_error == DISPATCH_FAILED_MESSAGE
    assert document.generation_completed_at is not None
    assert harness.calls[-1] == "commit"


# ---------------------------------------------------------------- regenerate


@pytest.mark.parametrize(
    "existing",
    [
        _document(LearningDocument.IN_PROGRESS, generation_started_at=datetime.now(UTC)),
        _document(LearningDocument.PENDING, celery_task_id="queued"),
    ],
)
async def test_regenerate_conflicts_while_generation_is_active(existing: LearningDocument):
    harness = _Harness(existing)

    with pytest.raises(AppError) as info:
        await harness.service.regenerate(TASK_ID)

    assert info.value.status_code == 409
    assert "생성" in info.value.message
    assert harness.dispatched == []


async def test_regenerate_dispatches_a_new_run_for_a_failed_document():
    existing = _document(LearningDocument.FAILED, generation_error="실패")
    harness = _Harness(existing)

    document = await harness.service.regenerate(TASK_ID)

    assert document.generation_status == LearningDocument.PENDING
    assert len(harness.dispatched) == 1


# ---------------------------------------------------------------- status lookups


async def test_get_document_returns_the_row_or_none():
    existing = _document(LearningDocument.COMPLETED)

    assert await _Harness(existing).service.get_document(TASK_ID) is existing
    assert await _Harness().service.get_document(TASK_ID) is None


async def test_mark_failed_stores_the_reason_and_completion_time():
    existing = _document(LearningDocument.IN_PROGRESS)
    harness = _Harness(existing)

    await harness.service.mark_failed(TASK_ID, "x" * 5000)

    assert existing.generation_status == LearningDocument.FAILED
    assert existing.generation_error is not None
    assert len(existing.generation_error) <= 2000
    assert existing.generation_completed_at is not None
    harness.session.commit.assert_awaited_once()


async def test_mark_failed_keeps_the_reason_of_a_row_that_already_failed():
    existing = _document(LearningDocument.FAILED, generation_error="유효한 챕터가 부족합니다")
    harness = _Harness(existing)

    await harness.service.mark_failed(TASK_ID, "일반 오류")

    assert existing.generation_error == "유효한 챕터가 부족합니다"
    harness.session.commit.assert_not_awaited()


async def test_mark_failed_without_a_row_is_a_no_op():
    harness = _Harness()

    await harness.service.mark_failed(TASK_ID, "사유")

    harness.session.commit.assert_not_awaited()


async def test_mark_pending_resets_the_status_for_a_celery_retry():
    existing = _document(LearningDocument.FAILED, generation_error="일시 오류")
    harness = _Harness(existing)

    await harness.service.mark_pending(TASK_ID)

    assert existing.generation_status == LearningDocument.PENDING
    assert existing.generation_error is None
    harness.session.commit.assert_awaited_once()


# ---------------------------------------------------------------- default dispatcher


async def test_default_dispatcher_sends_the_task_to_the_document_generation_queue(
    monkeypatch: pytest.MonkeyPatch,
):
    fake_task = MagicMock()
    module = types.ModuleType("src.tasks.document_generation")
    module.generate_document_task = fake_task  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "src.tasks.document_generation", module)
    harness = _Harness()
    service = DocumentQueueService(harness.session)  # no dispatch override

    document = await service.enqueue(TASK_ID)

    fake_task.apply_async.assert_called_once()
    kwargs = fake_task.apply_async.call_args.kwargs
    assert kwargs["args"] == [str(TASK_ID)]
    assert kwargs["queue"] == "document_generation"
    assert kwargs["task_id"] == document.celery_task_id


# ---------------------------------------------------------------- pure helpers


def test_failed_chapters_lists_chapters_marked_as_failed_in_order():
    content = {key: {"title": "t"} for key in LearningDocument.CHAPTER_KEYS}
    content["chapter6"] = {"generation_failed": True}
    content["chapter4"] = {"generation_failed": True}

    assert failed_chapters(content) == ["chapter4", "chapter6"]
    assert failed_chapters({key: {} for key in LearningDocument.CHAPTER_KEYS}) == []


@pytest.mark.parametrize(
    ("status", "started", "expected"),
    [
        (LearningDocument.IN_PROGRESS, NOW - timedelta(seconds=30), 150),
        (LearningDocument.IN_PROGRESS, NOW, 180),
        (LearningDocument.IN_PROGRESS, NOW - timedelta(seconds=400), 0),
        (LearningDocument.IN_PROGRESS, None, None),
        (LearningDocument.PENDING, None, None),
        (LearningDocument.COMPLETED, NOW - timedelta(seconds=30), None),
        (LearningDocument.FAILED, NOW - timedelta(seconds=30), None),
    ],
)
def test_estimated_remaining_seconds_counts_down_from_180_only_while_in_progress(
    status: str, started: datetime | None, expected: int | None
):
    document = _document(status, generation_started_at=started)

    assert estimate_remaining_seconds(document, now=NOW) == expected
