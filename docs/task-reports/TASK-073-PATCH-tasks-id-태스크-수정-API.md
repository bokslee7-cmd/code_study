# TASK-073. PATCH tasks id 태스크 수정 API

## 상태
완료

## 날짜
2026-11-16

## 작업 요약
`PATCH /api/v1/tasks/{task_id}` JSON `{title?, description?}` -> `TaskResponse`. 보낸 필드만 수정하며 `description: null`은 설명 삭제, `title: null`은 400. `task_number` 등 다른 키는 무시된다(불변).

오류: 400(제목 5~255자, 설명 500자 초과), 401, 403, 404.

## 변경 파일
- `backend/src/api/tasks.py`, `backend/src/api/schemas/task.py`, `backend/tests/unit/test_tasks_api.py` (공용)
- `specs/001-ai-code-learning-platform/tasks.md` (T073 완료 표시)

## TDD 결과
- RED: 구현 전 테스트를 먼저 작성하고 실행해 수집 단계 오류(모듈/라우트 부재)로 실패함을 확인함
- GREEN: 최소 구현 후 통과 확인
- REFACTOR: black / ruff / mypy 통과 확인
- 전체 백엔드: 736 passed, 47 skipped (이전 608 passed, 43 skipped). skipped는 PostgreSQL이 필요한 통합 테스트로, 이 환경에 DB가 없어 실행되지 않음
- 커밋: Git 저장소가 아니라 없음
- 이 엔드포인트 테스트: 부분 수정, null 설명, null 제목 거부, task_number 무시, 서비스 오류 전달

## 기술 결정
- `ProjectUpdate`와 같은 `exclude_unset` 방식으로 "안 보냄"과 "null"을 구분한다.

## 비고
- 라우트는 `backend/src/api/router.py`에 `tasks.router` 한 줄만 추가해 등록했다. 서비스 의존성(`get_task_service`, `get_code_upload_service`)은 `dependencies.py`에 추가했다.

