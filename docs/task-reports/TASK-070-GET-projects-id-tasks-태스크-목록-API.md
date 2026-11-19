# TASK-070. GET projects id tasks 태스크 목록 API

## 상태
완료

## 날짜
2026-11-16

## 작업 요약
`GET /api/v1/projects/{project_id}/tasks`: 프로젝트의 활성 태스크를 번호순으로 반환한다. 응답 `{ "tasks": [TaskResponse] }`.

`TaskResponse`: `id`, `project_id`, `task_number`, `title`, `description`, `upload_method`, `created_at`, `updated_at`, `uploaded_code`(`detected_language`, `complexity_level`, `total_lines`, `total_files`, `upload_size_bytes` 또는 null).

오류: 401(미로그인), 403(남의 프로젝트), 404(없거나 휴지통 프로젝트), 400(잘못된 UUID).

## 변경 파일
- `backend/src/api/tasks.py` (신규, T070~T075 공용)
- `backend/src/api/schemas/task.py` (신규)
- `backend/src/api/dependencies.py`, `backend/src/api/router.py` (등록)
- `backend/tests/unit/test_tasks_api.py` (신규, T070~T075 공용 37개)
- `specs/001-ai-code-learning-platform/tasks.md` (T070 완료 표시)

## TDD 결과
- RED: 구현 전 테스트를 먼저 작성하고 실행해 수집 단계 오류(모듈/라우트 부재)로 실패함을 확인함
- GREEN: 최소 구현 후 통과 확인
- REFACTOR: black / ruff / mypy 통과 확인
- 전체 백엔드: 736 passed, 47 skipped (이전 608 passed, 43 skipped). skipped는 PostgreSQL이 필요한 통합 테스트로, 이 환경에 DB가 없어 실행되지 않음
- 커밋: Git 저장소가 아니라 없음
- 이 엔드포인트 테스트: 인증, 목록, 빈 목록, 404/403, 잘못된 ID

## 기술 결정
- 목록 응답 래퍼는 `ProjectListResponse`(`{projects: [...]}`)와 같은 형태로 맞췄다.
- 서비스는 모의 객체로 대체해 HTTP 계약만 테스트한다(기존 projects API 테스트와 동일 방식).

## 비고
- 라우트는 `backend/src/api/router.py`에 `tasks.router` 한 줄만 추가해 등록했다. 서비스 의존성(`get_task_service`, `get_code_upload_service`)은 `dependencies.py`에 추가했다.
- 페이지네이션은 스펙에 없어 넣지 않았다(프로젝트당 최대 1000개 태스크 가정).
