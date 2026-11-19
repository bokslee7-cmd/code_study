# TASK-008. Alembic 마이그레이션 프레임워크 설정

## 상태
완료

## 날짜
2026-10-29

## 작업 요약
`backend/`에 Alembic을 비동기(async) 템플릿으로 초기화했다.
- `alembic.ini`: `script_location = alembic`, DB URL은 비워 둠(자격 증명 없음)
- `alembic/env.py`: `DATABASE_URL` 환경변수를 읽고, `postgresql://`를 `postgresql+asyncpg://`로 변환해 사용. 환경변수가 없으면 `RuntimeError`로 명확히 실패
- `alembic/versions/`: 빈 디렉터리(`.gitkeep`). 실제 스키마 마이그레이션은 T009에서 만든다.

## 변경 파일
- backend/alembic.ini (신규)
- backend/alembic/env.py, script.py.mako, README, versions/.gitkeep (신규)
- backend/tests/unit/test_alembic_setup.py (신규)
- backend/tests/unit/test_project_config.py (줄 길이 린트 수정)

## TDD 결과
- RED 커밋: 해당 없음 (Git 저장소 아님). 스캐폴드 없는 상태에서 6개 테스트 전부 실패 확인.
- GREEN 커밋: 해당 없음. 구현 후 6개 통과(오프라인 SQL 생성, `DATABASE_URL` 누락 시 오류, 실제 Postgres에 `alembic current` 연결 포함).
- REFACTOR 커밋: 해당 없음. 린트 정리와 `%` 이스케이프 보강 후 28개 단위 테스트 전체 통과.
- 테스트 커버리지: 해당 없음 (설정/스캐폴드)

추가 검증: `ruff check`, `black --check` 통과. 실행 중인 Docker PostgreSQL 15에 실제로 연결해 확인했다.

## 기술 결정
- **async 템플릿 + asyncpg**: requirements.txt에 동기 드라이버(psycopg2)가 없고 asyncpg만 있어서다. 앱의 SQLAlchemy 2.0 비동기 구성과도 맞는다.
- **URL은 환경변수 단일 출처**: ini에 비밀번호를 두지 않는다(constitution V). `.env.example`의 `DATABASE_URL` 형식(`postgresql://`)을 그대로 쓴다.
- **`%` 이스케이프**: configparser가 `%`를 보간 문자로 해석해, URL 인코딩된 비밀번호가 깨지는 것을 막는다.
- **`target_metadata = None`**: T009에서 `base.py`의 Base를 만든 뒤 연결한다. T009는 수동 SQL 마이그레이션이라 autogenerate는 쓰지 않는다.

## 비고
- `alembic.ini`의 `file_template`과 로깅 설정은 기본값이다.
- 사용법: `cd backend && DATABASE_URL=postgresql://... .venv/Scripts/python -m alembic current`
- 이 PC에서 `DATABASE_URL` 환경변수는 자동 설정되지 않는다. `.env`를 읽는 로직은 T011(설정)에서 만든다.
- Git 저장소가 아니라 커밋은 없다.
- 다음 작업: T009(base 모델 + 초기 마이그레이션).
