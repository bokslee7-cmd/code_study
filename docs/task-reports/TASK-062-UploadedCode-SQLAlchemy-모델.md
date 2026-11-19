# TASK-062. UploadedCode SQLAlchemy 모델

## 상태
완료

## 날짜
2026-11-12

## 작업 요약
`uploaded_code` 테이블에 대응하는 `UploadedCode` 모델을 만들었다. 태스크 하나당 업로드 분석 요약이 정확히 하나(1:1)이며, 컬럼·타입·NULL 허용 여부, 복잡도 체크(`beginner/intermediate/advanced`), 업로드 크기 체크(10 MiB 이하), `task_id` 유니크 제약, `idx_uploaded_code_task_id` 인덱스를 T009 마이그레이션과 같은 이름으로 맞췄다. `Task.uploaded_code` ↔ `UploadedCode.task` 1:1 관계를 추가했고, 태스크 삭제 시 삭제는 DB `ON DELETE CASCADE`에 맡긴다(`passive_deletes`).

## 변경 파일
- `backend/src/models/uploaded_code.py` (신규)
- `backend/src/models/task.py` (`uploaded_code` 관계 추가)
- `backend/src/models/__init__.py` (`UploadedCode` export)
- `backend/tests/unit/test_uploaded_code_model.py` (신규, 15개 테스트)
- `specs/001-ai-code-learning-platform/tasks.md` (T062 완료 표시)

## TDD 결과
- RED: `from src.models import UploadedCode` ImportError로 수집 단계 실패 확인
- GREEN: 신규 15개 통과, 전체 백엔드 487개 통과
- REFACTOR: ruff·black·mypy(src/models) 통과
- 테스트 커버리지: `src/models/uploaded_code.py` 100%
- 커밋: Git 저장소가 아니라 없음

## 기술 결정
- 이 테이블에는 `updated_at`이 없어서 `TimestampMixin`을 쓰지 않고 `created_at`만 직접 선언했다(`RefreshToken`과 같은 방식).
- 유니크 제약은 `unique=True` 대신 `UniqueConstraint(..., name="uploaded_code_task_id_key")`로 선언했다. 프로젝트의 naming convention이 `uq_...` 이름을 만들어 마이그레이션의 실제 이름(`uploaded_code_task_id_key`)과 어긋나기 때문이다.
- 개발 DB에 사용자→프로젝트→태스크→UploadedCode를 flush해 스키마 일치를 확인했고, 같은 `task_id`로 두 번째 행을 넣으면 IntegrityError로 거부되는 것도 확인했다(롤백해서 데이터는 남지 않음).

## 비고
- `UploadedCode.code_files` 관계는 T063(CodeFile 모델)에서 `CodeFile` 쪽 관계와 함께 추가한다.
- 다음: T063(CodeFile).
