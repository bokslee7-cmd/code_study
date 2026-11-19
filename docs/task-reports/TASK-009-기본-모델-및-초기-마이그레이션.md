# TASK-009. 기본 모델 클래스와 초기 DB 마이그레이션

## 상태
완료

## 날짜
2026-10-29

## 작업 요약
- `backend/src/models/base.py`: SQLAlchemy 2.0 `Base`(제약 이름 규칙 포함), `UUIDPrimaryKeyMixin`(서버 기본값 `gen_random_uuid()`), `TimestampMixin`(`created_at`, `updated_at`)
- `backend/alembic/versions/001_initial_schema.py`: data-model.md의 10개 테이블(users, projects, tasks, uploaded_code, code_files, learning_documents, practice_problems, questions, progress, refresh_tokens)과 인덱스 24개, CHECK/UNIQUE/FK 제약을 수동 SQL로 생성. 자동 생성(autogenerate)은 쓰지 않음. `downgrade`는 역순으로 테이블 삭제
- `alembic/env.py`의 `target_metadata`를 `Base.metadata`로 연결 (T008 후속)

## 변경 파일
- backend/src/__init__.py, backend/src/models/__init__.py (신규, 빈 파일)
- backend/src/models/base.py (신규)
- backend/alembic/versions/001_initial_schema.py (신규)
- backend/alembic/env.py (수정)
- backend/tests/unit/test_base_model.py (신규)
- backend/tests/integration/test_initial_migration.py (신규)

## TDD 결과
- RED 커밋: 해당 없음 (Git 저장소 아님). base.py가 없어 단위 테스트 import 실패, 마이그레이션 통합 테스트 19개 실패 확인.
- GREEN 커밋: 해당 없음. 구현 후 신규 23개(단위 3 + 통합 20) 통과, 백엔드 전체 51개 통과.
- REFACTOR 커밋: 해당 없음. ruff·black 정리 후 재통과.
- 테스트 커버리지: src 100% (base.py 13문장)

통합 테스트는 실행마다 임시 데이터베이스(`migration_test_*`)를 만들어 `upgrade head` → 제약 검증 → `downgrade base` 후 삭제한다. 개발 DB(`codelearning`)는 건드리지 않는다. 검증 항목: 테이블 10개·인덱스 24개 존재, 기본값(skill_level, deletion_status), 잘못된 행 거부 15종(이메일 형식, 중복, 빈 제목, task 제목 5자 미만, 업로드 10MB 초과, 7챕터 누락, 문제 번호 범위, 진행률 범위 등), 사용자 삭제 시 CASCADE, upgrade→downgrade→upgrade 반복.
`mypy src` 통과.

## 기술 결정
- **수동 SQL (`op.execute`)**: tasks.md 지시(autogenerate 금지)와 data-model.md의 부분 인덱스·CHECK·JSONB 제약을 그대로 재현하기 위함.
- **Base의 제약 이름 규칙**: 이후 T023~ 모델에서 일관된 이름을 쓰기 위함. 단, 마이그레이션의 제약 이름은 data-model.md의 이름을 그대로 쓴다.
- **개발 DB에는 아직 적용하지 않음**: 테스트만 임시 DB에 적용했다. 적용하려면 `DATABASE_URL=… alembic upgrade head`.

## 비고
- data-model.md 사양을 그대로 옮겼다. 사양 자체에 다음 특이점이 있으나 바꾸지 않았다: `uploaded_code.task_id`·`learning_documents.task_id`·`progress.task_id`는 UNIQUE라서 별도 인덱스가 중복이다. `progress`는 `task_id` 단독 UNIQUE라 사용자별 진행이 아니라 태스크당 1행이다. `users.email`의 CHECK 정규식은 `[A-Z|a-z]`에 `|` 문자를 허용한다.
- T023~ 모델은 이 마이그레이션 스키마와 일치해야 한다(tasks.md 명시).
- Git 저장소가 아니라 커밋은 없다.
- 다음 작업: T010(DB 세션), T011(DB 설정)은 병렬 가능.
