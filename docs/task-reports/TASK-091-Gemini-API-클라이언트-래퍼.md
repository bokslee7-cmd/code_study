# TASK-091. Gemini API 클라이언트 래퍼

## 상태
완료

## 날짜
2026-11-17

## 작업 요약
`GeminiClient`를 만들었다. `await client.generate(prompt, system_instruction=..., temperature=..., max_output_tokens=..., timeout=...)`가 응답 텍스트를 돌려주고, 모든 실패는 `GeminiError` 계열 예외로 바뀐다. 각 예외에는 `retryable` 플래그가 있어 T093의 재시도 로직이 이를 보고 판단하면 된다. 클라이언트 자체는 재시도하지 않는다.

| 예외 | 상황 | retryable |
|---|---|---|
| `GeminiConfigError` | `GOOGLE_API_KEY` 없음, 또는 `.env.example`의 자리표시자 값 | 아니오 |
| `GeminiTimeoutError` | 기본 180초(research.md의 문서 생성 제한) 안에 응답 없음 | 예 |
| `GeminiAPIError` | 429, 503, 500, DeadlineExceeded, GatewayTimeout, TooManyRequests | 예 |
| `GeminiAPIError` | InvalidArgument, PermissionDenied, NotFound 등 | 아니오 |
| `GeminiEmptyResponseError` | 텍스트 없는 응답(프롬프트 차단, 토큰 소진). `finish_reason` 포함 | 아니오 |

모델 이름은 `GOOGLE_MODEL` 환경 변수를 따르고, 없으면 `gemini-3-flash-preview`를 쓴다.

## 변경 파일
- `backend/src/services/ai/gemini_client.py` (신규)
- `backend/src/services/ai/__init__.py` (신규, 빈 파일)
- `backend/tests/unit/test_gemini_client.py` (신규, 21개)
- `backend/pyproject.toml` (mypy: `google.generativeai.*` 타입 정보 없음 override 추가)
- `specs/001-ai-code-learning-platform/tasks.md` (T091 완료 표시)

## TDD 결과
- RED: 모듈이 없어 테스트 수집 단계에서 실패하는 것을 확인했다.
- GREEN: 21개 통과, `gemini_client.py` 커버리지 100%. 전체 백엔드 스위트 823개 통과(이후 한 줄 수정 뒤 관련 35개 재통과), ruff·black·mypy(strict) 이상 없음.
- 실제 API 확인(단위 테스트는 가짜 모델만 사용하므로 별도로 수행): `GeminiClient.from_env()`로 `gemini-3-flash-preview`를 2회 호출했다. 정상 호출은 `'OK'`를 돌려줬고, `max_output_tokens=20`은 `GeminiEmptyResponseError(finish_reason=MAX_TOKENS)`로 바뀌었다. 프롬프트는 "Reply with the single word OK."뿐이다.
- 커밋 해시: 없음(git 저장소가 아님).

## 기술 결정
- **SDK는 고정된 google-generativeai 0.3.0을 그대로 썼다.** 이 버전에는 JSON 모드(`response_mime_type`)와 `system_instruction`이 없어서, 시스템 지시문은 프롬프트 앞에 붙이고(`"{system}\n\n{prompt}"`) JSON 출력은 호출자가 프롬프트로 요청하고 직접 파싱해야 한다. research.md가 "native JSON mode"를 전제로 쓴 부분과 다른 점이다. SDK를 올리면(또는 새 `google-genai`로 옮기면) 이 클래스 안에서만 바꾸면 되도록 호출부를 `generate()` 하나로 좁혀 뒀다.
- **`response.text`를 쓰지 않는다.** Gemini 3는 내부 사고 토큰도 `max_output_tokens`에서 쓰기 때문에 값이 작으면 응답에 `parts`가 비고, 0.3.0의 `response.text`가 `IndexError`를 낸다(실제로 재현함). parts를 직접 읽고 비면 `GeminiEmptyResponseError`를 낸다.
- `genai.configure(api_key=...)`는 SDK 0.3.0이 전역 상태로만 키를 받아서 `from_env()`에서 한 번 호출한다. 키는 `repr`에 나오지 않고 로그에도 남기지 않는다. 로그는 모델명·소요 시간·글자 수·오류 종류만 남긴다(프롬프트 본문은 남기지 않는다).
- 가짜 모델을 주입하는 `model=` 인자를 둬서 테스트가 네트워크 없이 돈다.

## 비고
- T092/T093에서 JSON을 받을 때는 `max_output_tokens`를 작게 주지 말아야 한다. 안 주는 것이 가장 안전하다. 주더라도 사고 토큰을 고려해 넉넉히 줘야 한다.
- 재시도(지수 백오프 3회)는 T093이 `retryable`을 보고 구현한다.
- 새 `google-genai` SDK로의 교체는 하지 않았다. 의존성 변경은 별도 결정이 필요하다.
