# TASK-090. LearningDocument SQLAlchemy 모델 (JSONB content)

## 상태
완료

## 날짜
2026-11-17

## 작업 요약
마이그레이션 001의 `learning_documents` 테이블과 같은 모양의 `LearningDocument` 모델을 만들었다. 태스크당 문서는 하나(`task_id` UNIQUE)이고, `content`는 JSONB로 chapter1~chapter7을 담는다. `Task.learning_document` 관계도 추가했다(uselist=False, passive_deletes=True. 삭제 연쇄는 DB의 ON DELETE CASCADE가 맡는다).

## 변경 파일
- `backend/src/models/learning_document.py` (신규)
- `backend/src/models/__init__.py` (export 추가)
- `backend/src/models/task.py` (`learning_document` 관계 추가)
- `backend/tests/unit/test_learning_document_model.py` (신규, 14개)
- `backend/tests/integration/test_learning_document_model_integration.py` (신규, 5개. 실제 PostgreSQL에 마이그레이션 적용)
- `specs/001-ai-code-learning-platform/tasks.md` (T090 완료 표시)

## TDD 결과
- RED: 두 테스트 파일이 `ImportError: cannot import name 'LearningDocument'`로 수집 단계에서 실패하는 것을 확인했다.
- GREEN: 단위 14개 + 통합 5개 = 19개 통과. 모델 파일 커버리지 100%(단위+통합 합산).
- 전체 백엔드 스위트 823개 통과, ruff·black·mypy(strict) 이상 없음.
- 커밋 해시: 없음(이 저장소는 git 저장소가 아님).
- 통합 테스트가 확인한 것: 기본값(`generation_status='pending'`, 타임스탬프), content 왕복 동일성, 같은 태스크의 두 번째 문서 거부(`learning_documents_task_id_key`), chapter 누락 거부(`valid_content_structure`), 잘못된 상태값 거부, 태스크 삭제 시 문서 연쇄 삭제.

## 기술 결정
- **제약 이름을 마이그레이션과 맞췄다.** `conv()`로 이름을 고정해 DB의 실제 이름(`learning_documents_task_id_key`, `learning_documents_generation_status_check`, `valid_content_structure`)과 일치시킨다. 기존 Task·UploadedCode 모델과 같은 방식이다.
- **`generation_status`는 nullable로 뒀다.** 마이그레이션이 `DEFAULT 'pending'`만 있고 NOT NULL이 아니기 때문이다. "마이그레이션과 일치" 요건을 우선했다. 상태가 NULL인 행이 생기지 않게 하려면 별도 마이그레이션이 필요하다.
- 마이그레이션처럼 `TimestampMixin`(created_at, updated_at)을 사용한다.

## 비고
- `content`는 NOT NULL이고 chapter1~7 키가 모두 있어야 INSERT된다. T094/T095에서 `pending` 상태의 빈 문서를 먼저 만들 때는 `{"chapter1": {}, ..., "chapter7": {}}` 같은 뼈대를 넣어야 한다.
- DB는 챕터 키의 존재만 검사한다. 각 챕터 안쪽 필드(title, concepts 등)의 구조 검증은 T092/T093(Pydantic 등)에서 해야 한다.
- 앞서 SQL로 테이블을 직접 검증했을 때(UNIQUE·CHECK 동작 확인)의 결과와 모델 테스트 결과가 같다.
- `pytest --cov`를 켜면 통합 테스트의 alembic 서브프로세스가 `Type <class 'object'> is already registered`로 실패한다. 커버리지 도구와 서브프로세스의 충돌이며 기존 통합 테스트 구조와 같은 문제다. `--cov` 없이는 통과한다.
