import copy
import json
from typing import Any

import pytest
from src.models.learning_document import CHAPTER_KEYS
from src.services.ai.gemini_client import (
    GeminiAPIError,
    GeminiConfigError,
    GeminiEmptyResponseError,
    GeminiTimeoutError,
)
from src.services.ai.prompts import PromptFile
from src.services.document.document_generation_service import (
    FAILED_CHAPTER_MARKER,
    DocumentGenerationError,
    DocumentGenerationService,
    parse_json_object,
)

FILES = [PromptFile(path="main.py", content="a = 1\nprint(a)\n")]

VALID_DOCUMENT: dict[str, Any] = {
    "chapter1": {"title": "이 코드가 하는 일", "summary": "숫자를 저장하고 보여 줍니다."},
    "chapter2": {
        "title": "기본 개념",
        "concepts": [
            {
                "name": "변수",
                "explanation": "값을 담는 상자",
                "analogy": "이름표 붙은 상자",
                "example": "a = 1",
                "use_cases": "값 저장",
            }
        ],
    },
    "chapter3": {
        "title": "구조",
        "flowchart": "시작\n  |\n끝",
        "file_breakdown": {"main.py": "메인 파일"},
    },
    "chapter4": {
        "title": "한 줄씩",
        "explanations": [
            {
                "file_path": "",
                "line_number": 1,
                "code": "a = 1",
                "what_it_does": "a에 1을 넣습니다.",
                "syntax_breakdown": "= 는 대입",
                "analogy": "",
                "alternatives": "",
                "important_notes": "",
            }
        ],
    },
    "chapter5": {
        "title": "실행 흐름",
        "steps": [
            {"step_number": 1, "action": "a 저장", "data_state": "a=1", "explanation": "상자에 1"}
        ],
    },
    "chapter6": {
        "title": "정리",
        "concepts": [
            {
                "concept_name": "변수",
                "what_it_is": "상자",
                "why_used": "저장",
                "where_applied": "1행",
            }
        ],
    },
    "chapter7": {
        "title": "실수",
        "mistakes": [
            {
                "mistake_title": "따옴표 빠짐",
                "wrong_code": "print(a",
                "right_code": "print(a)",
                "why_it_matters": "오류가 납니다",
                "how_to_fix": "괄호를 닫습니다",
            }
        ],
    },
}


def _doc(**overrides: Any) -> dict[str, Any]:
    document = copy.deepcopy(VALID_DOCUMENT)
    document.update(overrides)
    return document


def _broken(*chapters: str) -> dict[str, Any]:
    return _doc(**{chapter: {"title": "빈 챕터"} for chapter in chapters})


class FakeClient:
    """Plays back scripted answers: a string is returned, an exception is raised."""

    def __init__(self, *script: str | Exception) -> None:
        self.script = list(script)
        self.calls: list[dict[str, Any]] = []

    async def generate(self, prompt: str, **kwargs: Any) -> str:
        self.calls.append({"prompt": prompt, **kwargs})
        step = self.script.pop(0)
        if isinstance(step, Exception):
            raise step
        return step


def _service(client: FakeClient) -> tuple[DocumentGenerationService, list[float]]:
    sleeps: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    return DocumentGenerationService(client, sleep=fake_sleep, jitter=lambda: 0.0), sleeps


async def _generate(client: FakeClient):
    service, sleeps = _service(client)
    result = await service.generate(FILES, language="python")
    return result, sleeps


def _retryable() -> GeminiAPIError:
    return GeminiAPIError("busy", retryable=True)


# ---- success path -------------------------------------------------------------------------


async def test_valid_answer_is_returned_after_one_call():
    client = FakeClient(json.dumps(VALID_DOCUMENT, ensure_ascii=False))
    result, sleeps = await _generate(client)
    assert result.content == VALID_DOCUMENT
    assert result.failed_chapters == ()
    assert result.attempts == 1
    assert len(client.calls) == 1
    assert sleeps == []


async def test_prompt_and_system_instruction_are_sent():
    client = FakeClient(json.dumps(VALID_DOCUMENT))
    await _generate(client)
    call = client.calls[0]
    assert "a = 1" in call["prompt"]
    assert call["system_instruction"]
    assert call["temperature"] == 0.7


async def test_markdown_fence_and_chatter_around_json_are_ignored():
    text = "Error: timeout\n\n```json\n" + json.dumps(VALID_DOCUMENT) + "\n```\n끝"
    result, _ = await _generate(FakeClient(text))
    assert result.content == VALID_DOCUMENT


async def test_unknown_top_level_keys_are_dropped():
    result, _ = await _generate(FakeClient(json.dumps({**VALID_DOCUMENT, "extra": 1})))
    assert set(result.content) == set(CHAPTER_KEYS)


# ---- parse_json_object --------------------------------------------------------------------


def test_parse_repairs_truncated_json():
    text = '{"a": {"b": [1, 2, {"c": "cut off'
    assert parse_json_object(text) == {"a": {"b": [1, 2, {"c": "cut off"}]}}


def test_parse_ignores_braces_inside_strings():
    assert parse_json_object('{"a": "}{"} trailing') == {"a": "}{"}


def test_parse_rejects_text_without_an_object():
    with pytest.raises(ValueError):
        parse_json_object("그냥 문장입니다")


def test_parse_rejects_non_object_json():
    with pytest.raises(ValueError):
        parse_json_object("[1, 2, 3]")


# ---- API failures -------------------------------------------------------------------------


async def test_retryable_api_errors_back_off_exponentially_then_succeed():
    client = FakeClient(_retryable(), GeminiTimeoutError("slow"), json.dumps(VALID_DOCUMENT))
    result, sleeps = await _generate(client)
    assert result.attempts == 3
    assert sleeps == [2, 4]


async def test_backoff_adds_jitter_and_is_capped_at_60_seconds():
    sleeps: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    client = FakeClient(_retryable(), json.dumps(VALID_DOCUMENT))
    service = DocumentGenerationService(client, sleep=fake_sleep, jitter=lambda: 0.5)
    await service.generate(FILES, language="python")
    assert sleeps == [2.5]
    assert DocumentGenerationService.backoff_delay(10, jitter=0.9) == 60


async def test_gives_up_after_three_retries():
    client = FakeClient(*[_retryable() for _ in range(4)])
    service, sleeps = _service(client)
    with pytest.raises(DocumentGenerationError):
        await service.generate(FILES, language="python")
    assert len(client.calls) == 4
    assert sleeps == [2, 4, 8]


async def test_non_retryable_api_error_fails_immediately():
    client = FakeClient(GeminiAPIError("bad key", retryable=False))
    service, sleeps = _service(client)
    with pytest.raises(DocumentGenerationError) as info:
        await service.generate(FILES, language="python")
    assert len(client.calls) == 1
    assert sleeps == []
    assert isinstance(info.value.__cause__, GeminiAPIError)


async def test_config_error_fails_immediately():
    client = FakeClient(GeminiConfigError("no key"))
    service, _ = _service(client)
    with pytest.raises(DocumentGenerationError):
        await service.generate(FILES, language="python")
    assert len(client.calls) == 1


async def test_empty_response_is_retried():
    client = FakeClient(GeminiEmptyResponseError("empty"), json.dumps(VALID_DOCUMENT))
    result, _ = await _generate(client)
    assert result.attempts == 2


# ---- content problems ---------------------------------------------------------------------


async def test_unparseable_answer_is_retried_with_the_problem_in_the_prompt():
    client = FakeClient("JSON이 아닙니다", json.dumps(VALID_DOCUMENT))
    result, sleeps = await _generate(client)
    assert result.attempts == 2
    assert sleeps == []
    assert "이전 응답의 문제점" not in client.calls[0]["prompt"]
    assert "JSON" in client.calls[1]["prompt"].split("이전 응답의 문제점")[1]
    assert client.calls[1]["temperature"] == 0.8


async def test_schema_problems_name_the_failing_chapter_in_the_retry_prompt():
    client = FakeClient(json.dumps(_broken("chapter4")), json.dumps(VALID_DOCUMENT))
    result, _ = await _generate(client)
    assert result.failed_chapters == ()
    assert "chapter4" in client.calls[1]["prompt"].split("이전 응답의 문제점")[1]


async def test_content_retries_stop_after_two_and_too_few_valid_chapters_fail():
    bad = json.dumps(_broken("chapter3", "chapter4", "chapter5"))  # only 4 valid
    client = FakeClient(bad, bad, bad)
    service, _ = _service(client)
    with pytest.raises(DocumentGenerationError) as info:
        await service.generate(FILES, language="python")
    assert len(client.calls) == 3
    assert info.value.problems


async def test_five_valid_chapters_are_accepted_as_partial_content():
    bad = json.dumps(_broken("chapter4", "chapter5"))
    result, _ = await _generate(FakeClient(bad, bad, bad))
    assert result.failed_chapters == ("chapter4", "chapter5")
    assert result.content["chapter4"] == {FAILED_CHAPTER_MARKER: True}
    assert result.content["chapter1"] == VALID_DOCUMENT["chapter1"]
    assert set(result.content) == set(CHAPTER_KEYS)


async def test_best_attempt_is_kept_for_partial_content():
    worse = json.dumps(_broken("chapter2", "chapter3", "chapter4"))
    better = json.dumps(_broken("chapter7"))
    result, _ = await _generate(FakeClient(worse, better, worse))
    assert result.failed_chapters == ("chapter7",)


async def test_missing_chapter_counts_as_failed():
    document = _doc()
    del document["chapter6"]
    result, _ = await _generate(FakeClient(*[json.dumps(document)] * 3))
    assert result.failed_chapters == ("chapter6",)


@pytest.mark.parametrize(
    ("chapter", "broken"),
    [
        ("chapter1", {"title": "t", "summary": "  "}),
        ("chapter2", {"title": "t", "concepts": []}),
        ("chapter2", {"title": "t", "concepts": ["문자열"]}),
        ("chapter3", {"title": "t", "flowchart": "", "file_breakdown": {}}),
        ("chapter4", {"title": "t", "explanations": [{"line_number": "1", "code": "x"}]}),
        (
            "chapter4",
            {"title": "t", "explanations": [{"line_number": 0, "code": "x", "what_it_does": "y"}]},
        ),
        ("chapter5", {"title": "t", "steps": [{"step_number": 1}]}),
        ("chapter6", {"title": "t", "concepts": [{"concept_name": "x"}]}),
        ("chapter7", {"title": "t", "mistakes": []}),
        ("chapter1", "문자열 챕터"),
    ],
)
async def test_each_chapter_shape_is_checked(chapter: str, broken: Any):
    document = json.dumps(_doc(**{chapter: broken}))
    result, _ = await _generate(FakeClient(document, document, document))
    assert result.failed_chapters == (chapter,)


@pytest.mark.parametrize("bad_text", ["[TODO] 나중에 쓰기", "<script>alert(1)</script>"])
async def test_placeholders_and_html_tags_are_rejected(bad_text: str):
    document = _doc(chapter1={"title": "t", "summary": bad_text})
    payload = json.dumps(document)
    result, _ = await _generate(FakeClient(payload, payload, payload))
    assert result.failed_chapters == ("chapter1",)


async def test_empty_files_raise_before_any_api_call():
    client = FakeClient()
    service, _ = _service(client)
    with pytest.raises(ValueError):
        await service.generate([], language="python")
    assert client.calls == []


async def test_api_and_content_retry_budgets_are_independent():
    client = FakeClient(_retryable(), "JSON 아님", _retryable(), json.dumps(VALID_DOCUMENT))
    result, sleeps = await _generate(client)
    assert result.attempts == 4
    assert sleeps == [2, 4]


def test_parse_repairs_cut_inside_an_escape_sequence():
    cut_text = '{"a": "줄\\"바꿈\\n끝\\'  # ends with one lone backslash
    assert parse_json_object(cut_text) == {"a": '줄"바꿈\n끝'}


def test_parse_repairs_a_trailing_comma():
    assert parse_json_object('{"a": [1, 2,') == {"a": [1, 2]}


def test_parse_reports_json_that_cannot_be_repaired():
    with pytest.raises(ValueError, match="JSON을 읽을 수 없습니다"):
        parse_json_object('{"a" 1}')
