# TASK-015. API 라우터 구조 (/api/v1)

## 상태
완료

## 날짜
2026-11-02

## 작업 요약
`backend/src/api/router.py`를 구현하고 `create_app()`에 연결했다.
- `API_V1_PREFIX = "/api/v1"`: 버전 prefix 상수.
- `create_api_router()`: prefix가 `/api/v1`인 루트 `APIRouter`를 반환하는 팩토리. 이후 기능 라우터(auth, projects, tasks, documents, practice, qa, progress, trash)는 이 함수 안에서 `include_router(...)`로 등록한다.
- `main.create_app()`이 `app.include_router(create_api_router())`로 마운트한다.
- `/health`는 버전 없는 경로로 그대로 둔다. (당시에는 `/api/v1/health`가 404였으나, 2026-11-03에 프론트엔드 연결 확인용으로 `/api/v1/health`를 추가했다. `/health`는 인프라 점검용으로 유지한다.)
- 아직 등록된 기능 라우터는 없으므로 `/api/v1/*`는 모두 404이며, 요청 ID 헤더와 CORS는 그대로 적용된다.
- `backend/src/api/__init__.py`를 추가해 다른 패키지와 같은 형태로 맞췄다.

## 변경 파일
- backend/src/api/router.py (신규)
- backend/src/api/__init__.py (신규, 빈 파일)
- backend/src/main.py (라우터 import 및 `include_router` 추가)
- backend/tests/unit/test_api_router.py (신규, 8개)
- specs/001-ai-code-learning-platform/tasks.md (T015 체크)

## TDD 결과
- RED 커밋: 해당 없음 (Git 저장소 아님). `src.api.router`가 없어 수집 단계 `ImportError` 확인.
- GREEN 커밋: 해당 없음. 구현 후 신규 8개 통과, 백엔드 전체 128개 통과 / 24개 skip.
- REFACTOR 커밋: 해당 없음. ruff가 지적한 import 정렬(I001)을 `--fix`로 수정한 뒤 ruff·black·mypy·pytest 재통과.
- 테스트 커버리지: `src/api/router.py` 100%, `src/main.py` 100%, 전체 97% (`src/db/session.py` 63%는 기존 DB 통합 테스트 skip 때문이며 이번 변경과 무관)

skip 수가 직전 실행(25개)과 이번 마지막 실행(24개)에서 1개 달랐다. 원인은 확인하지 않았다. PostgreSQL이 필요한 기존 통합 테스트가 대부분 skip된 상태다.

## 기술 결정
- **모듈 전역 `api_router` 대신 팩토리 `create_api_router()`**: `create_app()`이 이미 팩토리 패턴이라 맞췄다. 전역 라우터를 쓰면 테스트에서 추가한 라우트가 다른 테스트로 새어 나간다.
- **prefix는 루트 라우터에 한 번만 지정**: 기능 라우터는 `/auth`, `/projects` 같은 상대 경로만 가진다. 버전을 올릴 때(`/api/v2`) 이 파일만 건드리면 된다.
- **`/health`는 버전 밖에 유지**: 로드밸런서·Docker 헬스체크는 API 버전과 무관해야 한다.
- **기능 라우터 스텁은 만들지 않음**: 빈 라우터 파일을 미리 만들면 사용되지 않는 코드가 생긴다. 각 엔드포인트 Task가 자기 라우터를 만들어 `create_api_router()`에 등록한다.

## 비고
- 인증 필요 라우터의 공통 의존성은 T027(`dependencies.py`)에서 다룬다.
- 예외 응답 형식은 T016(`exceptions.py`), 요청 로깅은 T193(`middleware.py`)의 범위다.
- Git 저장소가 아니라 커밋은 없다.
- 다음 작업: T016 (오류 처리 미들웨어 및 예외 스키마).
