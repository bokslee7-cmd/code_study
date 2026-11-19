import asyncio
import logging
import os
import time
from typing import Any, Protocol

import google.generativeai as genai
from google.api_core import exceptions as google_exceptions

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "gemini-3-flash-preview"
DEFAULT_TIMEOUT_SECONDS = 180.0  # research.md: 3 minutes for document generation
_PLACEHOLDER_KEY = "your-google-ai-api-key-here"  # value in .env.example

_RETRYABLE_GOOGLE_ERRORS = (
    google_exceptions.ResourceExhausted,
    google_exceptions.ServiceUnavailable,
    google_exceptions.InternalServerError,
    google_exceptions.DeadlineExceeded,
    google_exceptions.GatewayTimeout,
    google_exceptions.TooManyRequests,
)


class GeminiError(Exception):
    """Base class. `retryable` tells the caller (T093) whether trying again can help."""

    retryable = False


class GeminiConfigError(GeminiError):
    pass


class GeminiAPIError(GeminiError):
    def __init__(self, message: str, *, retryable: bool) -> None:
        super().__init__(message)
        self.retryable = retryable


class GeminiTimeoutError(GeminiError):
    retryable = True


class GeminiEmptyResponseError(GeminiError):
    """The API answered without any text (blocked prompt, or the token budget ran out)."""

    def __init__(self, message: str, *, finish_reason: str | None = None) -> None:
        super().__init__(message)
        self.finish_reason = finish_reason


class _GenerativeModel(Protocol):
    async def generate_content_async(self, contents: Any, **kwargs: Any) -> Any:
        ...


def _name(value: Any) -> str:
    return str(getattr(value, "name", value))


class GeminiClient:
    """Thin async wrapper around google-generativeai that turns every failure into a GeminiError.

    Limits of the pinned SDK (0.3.0): no JSON mode and no system_instruction parameter, so
    system text is put in front of the prompt and callers must ask for JSON in the prompt and
    parse it themselves. Retrying is left to the caller (see `retryable` on the errors).
    """

    def __init__(self, *, model_name: str = DEFAULT_MODEL, model: _GenerativeModel | None = None):
        self.model_name = model_name
        self._model: _GenerativeModel = model or genai.GenerativeModel(model_name)

    @classmethod
    def from_env(cls) -> "GeminiClient":
        api_key = os.environ.get("GOOGLE_API_KEY", "").strip()
        if not api_key or api_key == _PLACEHOLDER_KEY:
            raise GeminiConfigError("GOOGLE_API_KEY 환경 변수에 실제 API 키를 설정해야 합니다.")
        model_name = os.environ.get("GOOGLE_MODEL", "").strip() or DEFAULT_MODEL
        genai.configure(api_key=api_key)  # SDK 0.3.0 keeps the key in global state
        return cls(model_name=model_name)

    def __repr__(self) -> str:
        return f"GeminiClient(model_name={self.model_name!r})"

    async def generate(
        self,
        prompt: str,
        *,
        system_instruction: str | None = None,
        temperature: float | None = None,
        max_output_tokens: int | None = None,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> str:
        contents = f"{system_instruction}\n\n{prompt}" if system_instruction else prompt
        kwargs: dict[str, Any] = {}
        config = {
            key: value
            for key, value in (
                ("temperature", temperature),
                ("max_output_tokens", max_output_tokens),
            )
            if value is not None
        }
        if config:
            kwargs["generation_config"] = config

        started = time.monotonic()
        try:
            response = await asyncio.wait_for(
                self._model.generate_content_async(contents, **kwargs), timeout
            )
        except TimeoutError as error:
            logger.warning("Gemini call timed out model=%s timeout=%ss", self.model_name, timeout)
            message = f"Gemini 응답이 {timeout:g}초 안에 오지 않았습니다."
            raise GeminiTimeoutError(message) from error
        except google_exceptions.GoogleAPIError as error:
            retryable = isinstance(error, _RETRYABLE_GOOGLE_ERRORS)
            logger.warning(
                "Gemini call failed model=%s error=%s retryable=%s",
                self.model_name,
                type(error).__name__,
                retryable,
            )
            raise GeminiAPIError(f"Gemini API 오류: {error}", retryable=retryable) from error

        text = self._extract_text(response)
        logger.info(
            "Gemini call ok model=%s seconds=%.2f chars=%d",
            self.model_name,
            time.monotonic() - started,
            len(text),
        )
        return text

    @staticmethod
    def _extract_text(response: Any) -> str:
        # response.text raises IndexError when there are no parts, so read the parts directly.
        candidates = list(response.candidates or [])
        if candidates:
            parts = list(candidates[0].content.parts or [])
            if parts:
                return "".join(part.text for part in parts)
            reason = _name(candidates[0].finish_reason)
            raise GeminiEmptyResponseError(
                f"Gemini가 빈 응답을 돌려줬습니다(finish_reason={reason}).", finish_reason=reason
            )
        block = getattr(response.prompt_feedback, "block_reason", None)
        block_reason = _name(block) if block else None
        raise GeminiEmptyResponseError(
            f"Gemini가 응답을 만들지 않았습니다(block_reason={block_reason}).",
            finish_reason=block_reason,
        )
