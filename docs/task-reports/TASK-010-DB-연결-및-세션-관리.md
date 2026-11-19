# TASK-010. 데이터베이스 연결 및 세션 관리

## 상태
완료

## 날짜
2026-10-29

## 작업 요약
`backend/src/db/session.py`를 구현했다.
- `get_database_url()`: `DATABASE_URL` 환경변수를 읽고, 없으면 `RuntimeError`
- `to_async_url()`: `postgresql://`, `postgres://`를 `postgresql+asyncpg://`로 변환
- `get_engine()`: 캐시된 `AsyncEngine` (`pool_pre_ping=True`)
- `get_session_factory()`: `async_sessionmaker` (`expire_on_commit=False`)
- `get_session()`: FastAPI 의존성. 요청이 성공하면 commit, 예외가 나면 rollback 후 다시 던지고, 세션은 항상 닫는다.

## 변경 파일
- backend/src/db/__init__.py (신규, 빈 파일)
- backend/src/db/session.py (신규)
- backend/tests/unit/test_db_session.py (신규)
- backend/tests/integration/test_db_session_integration.py (신규)

## TDD 결과
- RED 커밋: 해당 없음 (Git 저장소 아님). 모듈이 없어 두 테스트 파일 모두 수집 단계에서 실패 확인.
- GREEN 커밋: 해당 없음. 구현 후 신규 10개 통과, 백엔드 전체 61개 통과.
- REFACTOR 커밋: 해당 없음. ruff·black 정리 후 재통과.
- 테스트 커버리지: src 100% (session.py 28문장)

통합 테스트는 임시 DB와 테이블을 만들어 확인한다: 쿼리 실행, 성공 시 commit(별도 연결에서 1행 확인), 예외 시 rollback(0행 확인), 세션 독립성. `mypy src`, `ruff`, `black` 통과.

## 기술 결정
- **엔진·팩토리 지연 생성 + `lru_cache`**: import 시점에 DB 설정을 요구하지 않아 테스트와 Alembic에서 안전하다.
- **`get_session`이 commit/rollback 담당**: 한 요청 = 한 트랜잭션. 서비스 레이어는 commit을 호출하지 않아도 된다(constitution III의 계층 규칙). 서비스에서 중간 확정이 필요하면 `flush()` 또는 별도 커밋 정책을 정해야 한다.
- **`expire_on_commit=False`**: 비동기 환경에서 commit 후 속성 접근 시 암묵적 I/O가 발생하는 문제를 막는다.
- **`pool_pre_ping=True`**: DB 재시작 후 끊긴 연결로 인한 첫 요청 실패를 방지한다.

## 비고
- 풀 크기(`pool_size`, `max_overflow`, `pool_recycle`)와 설정 객체는 T011(db/config.py)에서 다룬다. 그때 `get_engine()`이 설정을 받도록 연결해야 한다. 지금은 `DATABASE_URL`을 환경변수에서 직접 읽는다.
- `alembic/env.py`에도 같은 URL 변환 로직이 있다. T011에서 설정이 정리되면 한 곳으로 합치는 것이 좋다.
- `get_session`의 commit은 응답이 만들어진 뒤에 실행될 수 있어, commit 실패는 응답 후 오류가 될 수 있다(FastAPI yield 의존성의 일반적인 특성). 필요하면 이후 엔드포인트별로 명시적으로 commit하도록 조정한다.
- Git 저장소가 아니라 커밋은 없다.
- 다음 작업: T011(DB 설정·커넥션 풀).
