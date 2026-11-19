# TASK-061. Task SQLAlchemy 모델

## 상태
완료

## 날짜
2026-11-12

## 작업 요약
`tasks` 테이블에 대응하는 `Task` 모델을 만들었다. 컬럼·타입·NOT NULL·체크 제약(제목 5자 이상, 설명 500자 이하, 업로드 방식 `file/folder/paste`, 삭제 상태 `active/trashed`)·프로젝트 내 `task_number` 유니크 제약·인덱스 4개를 T009 마이그레이션과 같은 이름으로 맞췄다. 소프트 삭제 필드(`deletion_status`, `trashed_at`, `scheduled_deletion_at`)도 포함한다. `Project.tasks` ↔ `Task.project` 양방향 관계를 추가했고, 프로젝트 삭제 시 태스크 삭제는 DB `ON DELETE CASCADE`에 맡긴다(`passive_deletes`).

## 변경 파일
- `backend/src/models/task.py` (신규)
- `backend/src/models/__init__.py` (`Task` export)
- `backend/src/models/project.py` (`tasks` 관계 추가)
- `backend/tests/unit/test_task_model.py` (신규, 15개 테스트)
- `specs/001-ai-code-learning-platform/tasks.md` (T061 완료 표시)

## TDD 결과
- RED: `from src.models import Task` ImportError로 수집 단계 실패 확인
- GREEN: 신규 15개 통과, 전체 백엔드 472개 통과
- REFACTOR: ruff·black·mypy(src/models) 통과로 정리
- 테스트 커버리지: `src/models/task.py` 100%
- 커밋: Git 저장소가 아니라 없음

## 기술 결정
- 순차 `task_number`는 컬럼과 `(project_id, task_number)` 유니크 제약만 모델이 담당한다. 다음 번호 부여는 서비스(T068)의 책임이다(계층 규칙: 비즈니스 로직은 Service).
- 실제 개발 DB에 사용자·프로젝트·태스크를 flush해서 모델과 스키마가 맞는지 확인했다(롤백해서 데이터는 남지 않음).

## 비고
- `.venv/Scripts/black.exe`, `mypy.exe`는 이 환경에서 출력 없이 종료 코드 1을 반환했다. `python -m black`, `python -m mypy`로 실행해 확인했다.
- 다음: T062(UploadedCode), T063(CodeFile) 모델 — 둘 다 [P]이며 `Task`를 참조한다.
