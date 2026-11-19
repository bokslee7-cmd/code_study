# TASK-016. 오류 처리 미들웨어 및 예외 스키마

## 상태
완료

## 날짜
2026-11-02

## 작업 요약
`backend/src/api/exceptions.py`를 구현하고 `create_app()`에 연결했다. 모든 오류 응답이 `requirements-addendum.md` FR-111의 형식으로 통일된다.
- `ErrorResponse`(pydantic): `error`, `message`, 선택 `details`, 선택 `suggestion`. 값이 없는 선택 필드는 응답에서 제외한다.
- `AppError(status_code, error, message, details, suggestion)`: 도메인 예외. 이후 서비스/라우터가 이것을 raise 하면 해당 상태 코드와 형식으로 응답한다.
- `HTTPException`(Starlette 포함): 상태 코드별 `error` 코드(`not_found`, `unauthorized`, `forbidden`, `method_not_allowed`, `conflict`, `gone`, `rate_limit_exceeded` 등)와 한국어 기본 메시지로 변환. 존재하지 않는 경로의 404, 405도 같은 형식이다. `detail`에 직접 쓴 문자열은 그대로 `message`로 쓰고, 헤더(`WWW-Authenticate`, `Allow`)는 유지한다. 매핑에 없는 상태는 4xx → `client_error`, 5xx → `server_error`.
- `RequestValidationError`: **400** + `validation_error`, `details.errors = [{field, message}]` (예: `body.title`, `query.n`).
- 처리되지 않은 예외: `unhandled_exception_middleware`가 잡아 `internal_server_error` + 일반 한국어 메시지(500)로 응답하고, 스택트레이스와 `request_id`를 ERROR로 로깅한다.
- `register_exception_handlers(app)` 한 번 호출로 위 핸들러와 미들웨어를 모두 등록한다. `create_app()`에서 가장 먼저 호출한다.

## 변경 파일
- backend/src/api/exceptions.py (신규)
- backend/src/main.py (import 및 `register_exception_handlers(app)` 호출 추가)
- backend/tests/unit/test_exceptions.py (신규, 21개)
- specs/001-ai-code-learning-platform/tasks.md (T016 체크)

## TDD 결과
- RED 커밋: 해당 없음 (Git 저장소 아님). `src.api.exceptions`가 없어 수집 단계 `ImportError` 확인.
- GREEN 커밋: 해당 없음. 구현 후 신규 20개 통과.
- REFACTOR 커밋: 해당 없음. ruff(E501)·black 지적을 정리하고, 커버리지에서 빠진 비표준 상태 코드 분기 테스트 1개를 추가했다. 이후 ruff·black·mypy(strict)·pytest 재통과.
- 테스트 커버리지: `src/api/exceptions.py` 100%, 전체 100%. 백엔드 전체 173개 통과.

## 기술 결정
- **검증 오류는 422가 아니라 400**: FR-111이 "Validation Errors (400)"으로 정의했다. FastAPI 기본(422)과 다르므로, 프론트엔드는 검증 실패를 400으로 받는다.
- **500 처리는 `exception_handler(Exception)`이 아닌 미들웨어**: `Exception` 핸들러는 가장 바깥(ServerErrorMiddleware)에서 실행되어 `X-Request-ID`와 CORS 헤더가 빠지고 예외가 다시 raise 된다. 가장 안쪽 미들웨어로 잡으면 요청 ID·CORS가 500 응답에도 붙는다. 그래서 `register_exception_handlers`를 다른 미들웨어보다 먼저 호출해야 한다.
- **검증 오류에 pydantic `input`/`ctx`를 넣지 않음**: 사용자가 제출한 값(비밀번호 등)이 응답에 되돌려지는 것을 막는다. 위치(`loc`)와 메시지(`msg`)만 노출한다.
- **500 응답에 예외 내용 미노출**: 내부 정보(DB 주소, 비밀 값)가 새지 않도록 일반 메시지만 반환하고 상세는 로그에만 남긴다.
- **오류 코드·메시지를 한 곳(`_STATUS_ERRORS`)에서 관리**: FR-111의 "메시지 상수 중앙화" 규칙을 따랐다.
- **`AppError` 하위 클래스는 만들지 않음**: 필요한 시점의 Task가 직접 서브클래싱한다.

## 비고
- 검증 오류의 `message`(필드별)는 pydantic 기본 영어 메시지다. 한국어 번역은 FR-111 전체 적용 시점에 별도로 다룬다.
- 429의 `retry_after`는 `details`에 넣어 표현할 수 있다. 속도 제한 Task에서 필요하면 전용 필드로 확장한다.
- 보안 이벤트 로깅(401/403 등, FR-110)과 요청 로깅은 T193(`middleware.py`) 범위라 포함하지 않았다.
- Git 저장소가 아니라 커밋은 없다.
- 다음 작업: T017 (Celery 앱 및 Redis 연결).
