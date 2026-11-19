import importlib
import sys
from collections.abc import Iterator
from typing import Any

import pytest


@pytest.fixture
def celery_app_module(monkeypatch: pytest.MonkeyPatch) -> Iterator[Any]:
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/2")
    sys.modules.pop("src.tasks.celery_app", None)
    module = importlib.import_module("src.tasks.celery_app")
    yield module
    sys.modules.pop("src.tasks.celery_app", None)


def test_celery_app_uses_redis_for_broker_and_result_backend(celery_app_module: Any) -> None:
    assert celery_app_module.app.conf.broker_url == "redis://localhost:6379/2"
    assert celery_app_module.app.conf.result_backend == "redis://localhost:6379/2"


def test_celery_app_configures_required_queues_and_timeout(celery_app_module: Any) -> None:
    queue_names = {queue.name for queue in celery_app_module.app.conf.task_queues}

    assert queue_names == {"default", "document_generation", "practice_generation", "cleanup"}
    assert celery_app_module.app.conf.task_default_queue == "default"
    assert celery_app_module.app.conf.task_time_limit == 300


def test_celery_app_accepts_only_json_tasks(celery_app_module: Any) -> None:
    assert celery_app_module.app.conf.task_serializer == "json"
    assert celery_app_module.app.conf.result_serializer == "json"
    assert celery_app_module.app.conf.accept_content == ["json"]


@pytest.mark.parametrize("redis_url", [None, "", "  "])
def test_get_redis_url_requires_a_nonblank_value(
    celery_app_module: Any,
    monkeypatch: pytest.MonkeyPatch,
    redis_url: str | None,
) -> None:
    if redis_url is None:
        monkeypatch.delenv("REDIS_URL", raising=False)
    else:
        monkeypatch.setenv("REDIS_URL", redis_url)

    with pytest.raises(RuntimeError, match="REDIS_URL"):
        celery_app_module.get_redis_url()
