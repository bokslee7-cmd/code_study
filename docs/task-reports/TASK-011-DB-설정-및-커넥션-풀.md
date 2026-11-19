# TASK-011. 데이터베이스 설정 및 커넥션 풀

## 상태
완료

## 날짜
2026-10-30

## 작업 요약
`backend/src/db/config.py`를 구현하고 `session.py`, `alembic/env.py`가 이를 사용하도록 연결했다.
- `PoolSettings` (frozen dataclass): `pool_size=5`, `max_overflow=10`, `pool_timeout=30`, `pool_recycle=1800`, `echo=False`
- `load_pool_settings()`: `DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, `DB_POOL_TIMEOUT`, `DB_POOL_RECYCLE`, `DB_ECHO` 환경변수를 읽는다. 비어 있으면 기본값, 잘못된 값(정수 아님, 범위 밖, 불리언 아님)은 변수 이름이 담긴 `ValueError`.
- `engine_kwargs()`: `PoolSettings`를 `create_async_engine` 인자로 변환 (`pool_pre_ping=True` 고정, `pool_recycle=0`은 SQLAlchemy의 비활성 값 `-1`로 변환)
- `get_database_url()`, `to_async_url()`: `session.py`와 `alembic/env.py`에 중복돼 있던 로직을 config.py 한 곳으로 통합
- `session.get_engine()`이 풀 설정을 적용하도록 변경 (`session`에서 기존 이름은 그대로 import 가능)

## 변경 파일
- backend/src/db/config.py (신규)
- backend/src/db/session.py (수정: config 사용, URL 함수 제거 후 재노출)
- backend/alembic/env.py (수정: config의 URL 함수 사용)
- backend/pyproject.toml (수정: mypy_path `src` → `.`)
- backend/tests/unit/test_db_config.py (신규)
- backend/tests/unit/test_alembic_setup.py (수정: env.py가 config를 통해 URL을 읽는지 확인하도록 변경)
- .env.example (수정: DB_* 풀 변수 추가)
- specs/001-ai-code-learning-platform/tasks.md (T011 체크)

## TDD 결과
- RED 커밋: 해당 없음 (Git 저장소 아님). `src.db.config` 모듈이 없어 테스트 수집 단계에서 ImportError 확인.
- GREEN 커밋: 해당 없음. 구현 후 `tests/unit` 58개 통과, 1개 skip.
- REFACTOR 커밋: 해당 없음. ruff·black·mypy 통과.
- 테스트 커버리지: `src/db/config.py` 100% (unit 테스트 기준)

**통합 테스트는 이번에 실행하지 못했다.** Docker Desktop이 꺼져 있어 PostgreSQL(localhost:5432)에 연결할 수 없었고, `test_db_session_integration.py`와 `test_initial_migration.py` 등 25개가 skip됐다. 그 결과 전체 실행 기준 `session.py` 커버리지는 63%로 보인다(TASK-010에서는 DB가 있어 100%). `get_session` 쪽 코드는 이번에 바꾸지 않았지만, DB를 켜고 통합 테스트를 다시 돌려 확인해야 한다.
`alembic upgrade head --sql`(offline) 테스트는 통과했다.

## 기술 결정
- **pydantic-settings를 쓰지 않고 dataclass + 환경변수로 구현**: 설정이 5개뿐이라 새 의존성 없이 충분하다. 앱 전체 설정 객체가 필요해지면(T012 이후) 그때 통합한다.
- **잘못된 설정은 시작 시점에 `ValueError`**: 조용히 기본값으로 대체하면 운영에서 풀 크기를 잘못 지정한 것을 알아채기 어렵다.
- **`pool_recycle=0` = 비활성**: 사용자에게는 0이 직관적이고, SQLAlchemy 내부 값(-1)은 `engine_kwargs`에서만 다룬다.
- **`pool_pre_ping`은 설정 항목으로 열지 않고 항상 켬**: TASK-010 결정 유지.
- **mypy_path를 `.`로 변경**: 코드가 `src.` 접두사로 import(alembic·tests와 동일)하는데 `mypy_path = "src"`이면 같은 파일이 `db.config`와 `src.db.config`로 중복 인식되어 오류가 난다.

## 비고
- TASK-010 비고의 후속 항목(풀 설정 연결, `alembic/env.py` URL 로직 통합)을 처리했다.
- Alembic은 `NullPool`을 계속 사용하므로 풀 설정의 영향을 받지 않는다.
- Git 저장소가 아니라 커밋은 없다.
- 다음 작업: T012 (백엔드 유틸).
