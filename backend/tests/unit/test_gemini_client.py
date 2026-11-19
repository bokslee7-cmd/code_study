import asyncio
from types import SimpleNamespace
from typing import Any

import pytest
from google.api_core import exceptions as google_exceptions
from src.services.ai.gemini_client import (
    DEFAULT_MODEL,
    GeminiAPIError,
    GeminiClient,
    GeminiConfigError,
    GeminiEmptyResponseError,
    GeminiError,
    GeminiTimeoutError,
)


def _response(*texts: str, finish: Any = "STOP") -> SimpleNamespace:
    parts = [SimpleNamespace(text=t) for t in texts]
    candidate = SimpleNamespace(content=SimpleNamespace(parts=parts), finish_reason=finish)
    return SimpleNamespace(
        candidates=[candidate], prompt_feedback=SimpleNamespace(block_reason=None)
    )


class FakeModel:
    def __init__(self, result: Any = None, error: Exception | None = None, delay: float = 0):
        self.result, self.error, self.delay = result, error, delay
        self.calls: list[dict[str, Any]] = []

    async def generate_content_async(self, contents: Any, **kwargs: Any) -> Any:
        self.calls.append({"contents": contents, **kwargs})
        if self.delay:
            await asyncio.sleep(self.delay)
        if self.error:
            raise self.error
        return self.result


def _client(model: FakeModel) -> GeminiClient:
    return GeminiClient(model=model)


async def test_generate_returns_the_response_text():
    model = FakeModel(_response("안녕하세요"))
    assert await _client(model).generate("인사해줘") == "안녕하세요"
    assert model.calls[0]["contents"] == "인사해줘"


async def test_multiple_parts_are_joined():
    assert await _client(FakeModel(_response("가", "나"))).generate("p") == "가나"


async def test_system_instruction_is_put_in_front_of_the_prompt():
    # google-generativeai 0.3.0 has no system_instruction parameter.
    model = FakeModel(_response("ok"))
    await _client(model).generate("질문", system_instruction="너는 선생님이다")
    assert model.calls[0]["contents"] == "너는 선생님이다\n\n질문"


async def test_generation_options_are_forwarded_only_when_given():
    model = FakeModel(_response("ok"))
    await _client(model).generate("p")
    assert model.calls[0].get("generation_config") is None

    await _client(model).generate("p", temperature=0.2, max_output_tokens=4000)
    assert model.calls[1]["generation_config"] == {"temperature": 0.2, "max_output_tokens": 4000}


async def test_empty_parts_raise_instead_of_index_error():
    # Gemini 3 thinking tokens can use the whole max_output_tokens budget -> no parts at all.
    with pytest.raises(GeminiEmptyResponseError, match="MAX_TOKENS") as info:
        await _client(FakeModel(_response(finish="MAX_TOKENS"))).generate("p")
    assert info.value.finish_reason == "MAX_TOKENS"
    assert info.value.retryable is False


async def test_blocked_prompt_is_reported_with_the_reason():
    response = SimpleNamespace(
        candidates=[], prompt_feedback=SimpleNamespace(block_reason="SAFETY")
    )
    with pytest.raises(GeminiEmptyResponseError, match="SAFETY"):
        await _client(FakeModel(response)).generate("p")


async def test_enum_like_finish_reason_uses_its_name():
    response = _response(finish=SimpleNamespace(name="SAFETY"))
    with pytest.raises(GeminiEmptyResponseError, match="SAFETY"):
        await _client(FakeModel(response)).generate("p")


async def test_timeout_raises_a_retryable_error():
    with pytest.raises(GeminiTimeoutError) as info:
        await _client(FakeModel(_response("late"), delay=1)).generate("p", timeout=0.01)
    assert info.value.retryable is True


@pytest.mark.parametrize(
    "error",
    [
        google_exceptions.ResourceExhausted("quota"),
        google_exceptions.ServiceUnavailable("down"),
        google_exceptions.InternalServerError("oops"),
        google_exceptions.DeadlineExceeded("slow"),
    ],
)
async def test_transient_google_errors_are_retryable(error: Exception):
    with pytest.raises(GeminiAPIError) as info:
        await _client(FakeModel(error=error)).generate("p")
    assert info.value.retryable is True
    assert info.value.__cause__ is error


@pytest.mark.parametrize(
    "error",
    [
        google_exceptions.InvalidArgument("bad"),
        google_exceptions.PermissionDenied("key"),
        google_exceptions.NotFound("model"),
    ],
)
async def test_permanent_google_errors_are_not_retryable(error: Exception):
    with pytest.raises(GeminiAPIError) as info:
        await _client(FakeModel(error=error)).generate("p")
    assert info.value.retryable is False


async def test_unexpected_errors_are_not_swallowed():
    with pytest.raises(ValueError):
        await _client(FakeModel(error=ValueError("bug"))).generate("p")


def test_all_client_errors_share_a_base_class():
    for error in (GeminiConfigError, GeminiAPIError, GeminiEmptyResponseError, GeminiTimeoutError):
        assert issubclass(error, GeminiError)


def test_from_env_requires_an_api_key(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    with pytest.raises(GeminiConfigError, match="GOOGLE_API_KEY"):
        GeminiClient.from_env()


def test_from_env_rejects_the_example_placeholder(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "your-google-ai-api-key-here")
    with pytest.raises(GeminiConfigError, match="GOOGLE_API_KEY"):
        GeminiClient.from_env()


def test_from_env_uses_google_model_with_a_default(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "real-looking-key")
    monkeypatch.delenv("GOOGLE_MODEL", raising=False)
    assert GeminiClient.from_env().model_name == DEFAULT_MODEL == "gemini-3-flash-preview"
    monkeypatch.setenv("GOOGLE_MODEL", "gemini-other")
    assert GeminiClient.from_env().model_name == "gemini-other"


def test_key_is_not_leaked_by_repr(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "super-secret-key")
    assert "super-secret-key" not in repr(GeminiClient.from_env())
