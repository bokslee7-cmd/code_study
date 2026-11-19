"""Generates the 7-chapter learning document with retries and validation (T093).

Flow per attempt: ask Gemini -> pull one JSON object out of the text (repairing a cut-off
answer) -> check every chapter. Two independent retry budgets apply (requirements-addendum
CHK006/CHK007/CHK013):
- API trouble (retryable error, empty answer): up to 3 retries, exponential backoff with jitter.
- Content trouble (not JSON, chapters that fail validation): up to 2 retries; the prompt then
  lists the problems and the temperature goes 0.7 -> 0.8.
If the last answer still has bad chapters, the best attempt is accepted when at least 5 of the 7
chapters are valid (bad ones become `{"generation_failed": true}`); otherwise it raises.
The "basic template" last resort of CHK006 is not implemented here.

`generate_document(task_id)` wraps this for one task: it reads the uploaded code, keeps the single
LearningDocument row's status (in_progress -> completed / failed) and stores the content.
"""

import asyncio
import json
import logging
import random
import re
import uuid
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.api.exceptions import NotFoundException
from src.models import LearningDocument, Task
from src.models.learning_document import CHAPTER_KEYS
from src.services.ai.gemini_client import GeminiEmptyResponseError, GeminiError
from src.services.ai.prompts import SYSTEM_INSTRUCTION, PromptFile, build_document_prompt
from src.services.code_analysis.code_upload_service import CodeUploadService

logger = logging.getLogger(__name__)

__all__ = [
    "FAILED_CHAPTER_MARKER",
    "DocumentGenerationError",
    "DocumentGenerationService",
    "GenerationResult",
    "parse_json_object",
]

FAILED_CHAPTER_MARKER = "generation_failed"
MAX_ERROR_LENGTH = 2000
TASK_NOT_FOUND_MESSAGE = (
    "학습 문서를 만들 태스크를 찾을 수 없습니다. 삭제되었거나 존재하지 않는 태스크입니다."  # noqa: E501 (Korean text is double width)
)
TASK_NOT_FOUND_SUGGESTION = "태스크 목록에서 태스크가 남아 있는지 확인한 뒤 다시 시도하세요."
MAX_API_RETRIES = 3
MAX_CONTENT_RETRIES = 2
MIN_VALID_CHAPTERS = 5
BASE_TEMPERATURE = 0.7
RETRY_TEMPERATURE = 0.8
BACKOFF_BASE_SECONDS = 2.0
BACKOFF_MAX_SECONDS = 60.0

# Fields that legitimately hold code, so "<" in them is not an HTML-injection sign.
_CODE_FIELDS = frozenset(
    {"code", "example", "wrong_code", "right_code", "alternatives", "flowchart", "syntax_breakdown"}
)
_PLACEHOLDER = re.compile(r"\[\s*(TODO|GENERATE)[^\]]*\]", re.IGNORECASE)
_DANGEROUS_TAG = re.compile(
    r"<\s*/?\s*(script|iframe|object|embed|style|link|meta)\b", re.IGNORECASE
)


class DocumentGenerationError(Exception):
    def __init__(self, message: str, *, problems: Sequence[str] = ()) -> None:
        super().__init__(message)
        self.problems = tuple(problems)


@dataclass(frozen=True)
class GenerationResult:
    content: dict[str, Any]  # always has chapter1..chapter7
    failed_chapters: tuple[str, ...]  # chapters replaced by the failure marker
    attempts: int  # number of Gemini calls made


class _TextGenerator(Protocol):
    async def generate(
        self,
        prompt: str,
        *,
        system_instruction: str | None = None,
        temperature: float | None = None,
        max_output_tokens: int | None = None,
        timeout: float = ...,
    ) -> str:
        ...


# ---- JSON extraction ----------------------------------------------------------------------


def _close_open_structures(text: str) -> str:
    """Append what a cut-off JSON text is missing: an open string and unclosed brackets."""
    stack: list[str] = []
    in_string = escaped = False
    for char in text:
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
        elif char == '"':
            in_string = True
        elif char in "{[":
            stack.append("}" if char == "{" else "]")
        elif char in "}]" and stack:
            stack.pop()
    if escaped:
        text = text[:-1]
    return text + ('"' if in_string else "") + "".join(reversed(stack))


def parse_json_object(text: str) -> dict[str, Any]:
    """Return the first JSON object in `text`, ignoring chatter and code fences around it.

    A cut-off object is repaired by closing it. Raises ValueError if there is no usable object.
    """
    start = text.find("{")
    if start == -1:
        raise ValueError("응답에 JSON 객체가 없습니다.")
    try:
        value, _ = json.JSONDecoder().raw_decode(text[start:])
    except json.JSONDecodeError:
        try:
            value = json.loads(_close_open_structures(text[start:].rstrip().rstrip(",")))
        except json.JSONDecodeError as error:
            raise ValueError(f"JSON을 읽을 수 없습니다: {error.msg}") from error
    if not isinstance(value, dict):
        raise ValueError("JSON 최상위 값이 객체가 아닙니다.")
    return value


# ---- validation ---------------------------------------------------------------------------


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _items(chapter: dict[str, Any], key: str, required: Sequence[str]) -> list[str]:
    items = chapter.get(key)
    if not isinstance(items, list) or not items:
        return [f"{key}가 비어 있거나 목록이 아닙니다."]
    problems = []
    for index, item in enumerate(items, 1):
        if not isinstance(item, dict):
            problems.append(f"{key}[{index}]가 객체가 아닙니다.")
            continue
        problems += [
            f"{key}[{index}].{name}가 비어 있습니다."
            for name in required
            if not _text(item.get(name))  # noqa: E501 (Korean text is double width)
        ]
    return problems


def _check_chapter1(chapter: dict[str, Any]) -> list[str]:
    return [] if _text(chapter.get("summary")) else ["summary가 비어 있습니다."]


def _check_chapter3(chapter: dict[str, Any]) -> list[str]:
    problems = [] if _text(chapter.get("flowchart")) else ["flowchart가 비어 있습니다."]
    if not isinstance(chapter.get("file_breakdown"), dict):
        problems.append("file_breakdown이 객체가 아닙니다.")
    return problems


def _check_chapter4(chapter: dict[str, Any]) -> list[str]:
    problems = _items(chapter, "explanations", ("code", "what_it_does"))
    for index, item in enumerate(chapter.get("explanations") or [], 1):
        number = item.get("line_number") if isinstance(item, dict) else None
        if isinstance(number, bool) or not isinstance(number, int) or number < 1:
            problems.append(f"explanations[{index}].line_number가 1 이상의 정수가 아닙니다.")
    return problems


_CHAPTER_CHECKS: dict[str, Callable[[dict[str, Any]], list[str]]] = {
    "chapter1": _check_chapter1,
    "chapter2": lambda c: _items(c, "concepts", ("name", "explanation")),
    "chapter3": _check_chapter3,
    "chapter4": _check_chapter4,
    "chapter5": lambda c: _items(c, "steps", ("action", "explanation")),
    "chapter6": lambda c: _items(c, "concepts", ("concept_name", "what_it_is")),
    "chapter7": lambda c: _items(c, "mistakes", ("mistake_title", "wrong_code", "right_code")),
}


def _unsafe_text(value: Any, key: str = "") -> str | None:
    """Describe the first placeholder or HTML tag found in `value`, or None."""
    if isinstance(value, str):
        if _PLACEHOLDER.search(value):
            return "자리표시 문구([TODO] 등)가 남아 있습니다."
        if key not in _CODE_FIELDS and _DANGEROUS_TAG.search(value):
            return "HTML 태그(script 등)가 들어 있습니다."
    elif isinstance(value, dict):
        children = list(value.items())
    elif isinstance(value, list):
        children = [(key, item) for item in value]
    else:
        return None
    if isinstance(value, dict | list):
        for child_key, child in children:
            found = _unsafe_text(child, str(child_key))
            if found:
                return found
    return None


def _validate_chapters(document: dict[str, Any]) -> tuple[dict[str, Any], dict[str, list[str]]]:
    """Split the answer into (valid chapters, problems per invalid chapter)."""
    valid: dict[str, Any] = {}
    invalid: dict[str, list[str]] = {}
    for key in CHAPTER_KEYS:
        chapter = document.get(key)
        if not isinstance(chapter, dict):
            invalid[key] = ["챕터가 없거나 객체가 아닙니다."]
            continue
        problems = _CHAPTER_CHECKS[key](chapter)
        unsafe = _unsafe_text(chapter)
        if unsafe:
            problems.append(unsafe)
        if problems:
            invalid[key] = problems
        else:
            valid[key] = chapter
    return valid, invalid


# ---- service ------------------------------------------------------------------------------


class DocumentGenerationService:
    def __init__(
        self,
        client: _TextGenerator,
        session: AsyncSession | None = None,
        *,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        jitter: Callable[[], float] = lambda: random.uniform(0, 1),  # noqa: S311
    ) -> None:
        self._client = client
        self._session = session
        self._sleep = sleep
        self._jitter = jitter

    @staticmethod
    def backoff_delay(retry_number: int, *, jitter: float) -> float:
        """Seconds to wait before API retry `retry_number` (0-based): min(60, 2 * 2^n + jitter)."""
        delay: float = BACKOFF_BASE_SECONDS * 2**retry_number + jitter
        return min(BACKOFF_MAX_SECONDS, delay)

    async def generate_document(self, task_id: uuid.UUID) -> LearningDocument:
        """Generate and store the document of one task; commits so the status is visible.

        Unlike the other services this commits itself: a poller must see `in_progress` while
        Gemini is still working. Raises NotFoundException (no such active task, or no code) and
        DocumentGenerationError (the row is then saved as `failed` with the reason).
        """
        if self._session is None:
            raise RuntimeError("generate_document에는 DB 세션이 필요합니다.")
        session = self._session
        task = (
            await session.execute(
                select(Task)
                .options(selectinload(Task.uploaded_code))
                .where(Task.id == task_id, Task.deletion_status == Task.ACTIVE)
            )
        ).scalar_one_or_none()
        if task is None:
            raise NotFoundException(
                TASK_NOT_FOUND_MESSAGE,
                details={"task_id": str(task_id)},
                suggestion=TASK_NOT_FOUND_SUGGESTION,
            )
        stored = await CodeUploadService(session).get_code(task)
        files = [
            PromptFile(item.file.file_path or item.file.file_name, item.content) for item in stored
        ]
        uploaded = task.uploaded_code
        language = (uploaded.detected_language if uploaded else None) or stored[0].language
        complexity = uploaded.complexity_level if uploaded else None

        document_id = await self._mark_in_progress(session, task_id)
        try:
            result = await self.generate(files, language=language, complexity_level=complexity)
        except Exception as error:
            reason = str(error)
            if isinstance(error, DocumentGenerationError):
                reason = "; ".join([reason, *error.problems])
            await self._finish(session, document_id, LearningDocument.FAILED, error=reason)
            raise
        note = (
            f"일부 챕터를 만들지 못했습니다: {', '.join(result.failed_chapters)}"
            if result.failed_chapters
            else None
        )
        return await self._finish(
            session, document_id, LearningDocument.COMPLETED, content=result.content, error=note
        )

    @staticmethod
    async def _mark_in_progress(session: AsyncSession, task_id: uuid.UUID) -> uuid.UUID:
        document = (
            await session.execute(
                select(LearningDocument).where(LearningDocument.task_id == task_id)
            )
        ).scalar_one_or_none()
        if document is None:
            document = LearningDocument(task_id=task_id, content={key: {} for key in CHAPTER_KEYS})
            session.add(document)
        document.generation_status = LearningDocument.IN_PROGRESS
        document.generation_started_at = datetime.now(UTC)
        document.generation_completed_at = None
        document.generation_error = None
        await session.commit()
        return document.id

    @staticmethod
    async def _finish(
        session: AsyncSession,
        document_id: uuid.UUID,
        status: str,
        *,
        content: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> LearningDocument:
        await session.rollback()  # drop whatever a failed step left half-done
        document = await session.get(LearningDocument, document_id)
        if document is None:  # deleted while generating (task removed)
            raise NotFoundException(TASK_NOT_FOUND_MESSAGE)
        if content is not None:
            document.content = content
        document.generation_status = status
        document.generation_completed_at = datetime.now(UTC)
        document.generation_error = error[:MAX_ERROR_LENGTH] if error else None
        await session.commit()
        return document

    async def generate(
        self,
        files: Sequence[PromptFile],
        *,
        language: str,
        complexity_level: str | None = None,
    ) -> GenerationResult:
        problems: list[str] = []
        api_retries = content_retries = attempts = 0
        best_valid: dict[str, Any] | None = None

        while True:
            prompt = build_document_prompt(
                files, language=language, complexity_level=complexity_level, problems=problems
            )
            temperature = RETRY_TEMPERATURE if content_retries else BASE_TEMPERATURE
            attempts += 1
            try:
                answer = await self._client.generate(
                    prompt, system_instruction=SYSTEM_INSTRUCTION, temperature=temperature
                )
            except GeminiError as error:
                if not (error.retryable or isinstance(error, GeminiEmptyResponseError)):
                    raise DocumentGenerationError(str(error)) from error
                if api_retries >= MAX_API_RETRIES:
                    message = f"Gemini 호출이 {attempts}번 실패했습니다: {error}"
                    raise DocumentGenerationError(message) from error
                delay = self.backoff_delay(api_retries, jitter=self._jitter())
                api_retries += 1
                logger.warning(
                    "Gemini retry %d/%d in %.1fs: %s", api_retries, MAX_API_RETRIES, delay, error
                )
                await self._sleep(delay)
                continue

            valid, invalid = self._inspect(answer)
            if not invalid:
                return GenerationResult(valid, (), attempts)
            problems = invalid.get("response") or [
                f"{key}: {problem}" for key, found in invalid.items() for problem in found
            ]
            logger.warning(
                "Gemini answer rejected attempt=%d problems=%s raw=%.1000s",
                attempts,
                problems,
                answer,
            )
            if best_valid is None or len(valid) > len(best_valid):
                best_valid = valid
            if content_retries >= MAX_CONTENT_RETRIES:
                return self._accept_partial(best_valid, problems, attempts)
            content_retries += 1

    @staticmethod
    def _inspect(answer: str) -> tuple[dict[str, Any], dict[str, list[str]]]:
        try:
            document = parse_json_object(answer)
        except ValueError as error:
            return {}, {"response": [f"응답이 올바른 JSON 객체가 아닙니다: {error}"]}
        return _validate_chapters(document)

    @staticmethod
    def _accept_partial(
        valid: dict[str, Any], problems: list[str], attempts: int
    ) -> GenerationResult:
        if len(valid) < MIN_VALID_CHAPTERS:
            raise DocumentGenerationError(
                f"유효한 챕터가 {len(valid)}개뿐이라 문서를 만들 수 없습니다."
                f"(최소 {MIN_VALID_CHAPTERS}개)",  # noqa: E501 (Korean text is double width)
                problems=problems,
            )
        failed = tuple(key for key in CHAPTER_KEYS if key not in valid)
        content = {key: valid.get(key, {FAILED_CHAPTER_MARKER: True}) for key in CHAPTER_KEYS}
        return GenerationResult(content, failed, attempts)
