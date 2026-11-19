# TASK-014. FastAPI 앱 초기화 (CORS, 미들웨어)

## 상태
완료

## 날짜
2026-10-30

## 작업 요약
`backend/src/main.py`를 구현했다.
- `create_app()`: FastAPI 앱 팩토리. 모듈 끝에서 `app = create_app()`로 uvicorn 진입점(`src.main:app`)을 제공.
- CORS: `ALLOWED_ORIGINS`(쉼표 구분, 기본 `http://localhost:5173`)의 출처만 허용하고 `allow_credentials=True`. 허용 메서드·헤더는 필요한 것만 명시. `*`가 들어 있으면 `ValueError`로 시작을 막는다.
- 요청 ID 미들웨어: 모든 응답에 `X-Request-ID`를 붙인다. 들어온 값이 `[A-Za-z0-9_-]{1,64}`이면 유지, 아니면 새 UUID(hex)로 교체. 브라우저에서 읽을 수 있게 `expose_headers`에 포함. `request.state.request_id`에도 저장.
- `GET /health`: `{"status": "ok"}` (DB·Redis 점검 없이 프로세스 생존만 확인)

## 변경 파일
- backend/src/main.py (신규)
- backend/tests/unit/test_main.py (신규, 20개)
- specs/001-ai-code-learning-platform/tasks.md (T014 체크)

## TDD 결과
- RED 커밋: 해당 없음 (Git 저장소 아님). `src.main`이 없어 수집 단계 오류 확인.
- GREEN 커밋: 해당 없음. 구현 후 main 테스트 20개 통과, 백엔드 전체 119개 통과 / 25개 skip.
- REFACTOR 커밋: 해당 없음. ruff·black·mypy 통과.
- 테스트 커버리지: `src/main.py` 100%

skip 25개는 PostgreSQL이 필요한 기존 통합 테스트로, Docker가 꺼져 있어 이번에도 실행하지 못했다. main.py는 DB를 쓰지 않는다.

## 기술 결정
- **`*` 출처 거부**: 인증을 HTTPOnly 쿠키로 하므로(research.md) `allow_credentials=True`가 필요하고, research.md도 출처 화이트리스트를 요구한다.
- **요청 ID 미들웨어를 CORS 안쪽에 등록**: 이후 오류 응답(T016)에도 CORS 헤더가 붙게 하기 위한 순서다. 요청 ID는 로그와 오류 응답을 연결하는 용도로 쓴다.
- **외부에서 온 요청 ID는 형식 검증 후 사용**: 그대로 쓰면 로그·헤더로 임의 문자열이 들어올 수 있다.
- **앱 팩토리 + 모듈 수준 `app`**: 테스트에서 환경변수를 바꿔 앱을 새로 만들 수 있고, 운영은 `src.main:app`을 그대로 쓴다.
- **라우터·예외 처리·DB 수명주기는 넣지 않음**: 각각 T015(`/api/v1` 라우터), T016(예외 처리)의 범위다.

## 비고
- T015에서 `create_app()` 안에서 `app.include_router(...)`를 호출하면 된다.
- T016의 예외 핸들러는 `request.state.request_id`를 응답 본문에 넣을 수 있다.
- 요구사항의 엔드포인트별 속도 제한(requirements-addendum CHK049)은 Redis 기반이라 이번 범위가 아니다.
- Git 저장소가 아니라 커밋은 없다.
- 다음 작업: T015 (API 라우터 구조).
