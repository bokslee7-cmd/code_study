# TASK-075. GET tasks id code 업로드 코드 조회 API

## 상태
완료

## 날짜
2026-11-16

## 작업 요약
`GET /api/v1/tasks/{task_id}/code` -> `TaskCodeResponse`.

필드: `task_id`, `detected_language`, `complexity_level`, `total_lines`, `total_files`, `upload_size_bytes`, `files[]`(`id`, `file_name`, `file_path`, `file_extension`, `file_size_bytes`, `language`, `content`).

오류: 401, 403, 404(태스크 없음/업로드 없음/저장 파일 유실).

## 변경 파일
- `backend/src/api/tasks.py`, `backend/src/api/schemas/task.py`, `backend/tests/unit/test_tasks_api.py` (공용)
- `specs/001-ai-code-learning-platform/tasks.md` (T075 완료 표시)

## TDD 결과
- RED: 구현 전 테스트를 먼저 작성하고 실행해 수집 단계 오류(모듈/라우트 부재)로 실패함을 확인함
- GREEN: 최소 구현 후 통과 확인
- REFACTOR: black / ruff / mypy 통과 확인
- 전체 백엔드: 736 passed, 47 skipped (이전 608 passed, 43 skipped). skipped는 PostgreSQL이 필요한 통합 테스트로, 이 환경에 DB가 없어 실행되지 않음
- 커밋: Git 저장소가 아니라 없음
- 이 엔드포인트 테스트: 요약+파일 내용, `storage_path` 비노출, 업로드 없음 404, 소유권 선검사

## 기술 결정
- 서버 내부 경로(`storage_path`)는 응답에 넣지 않는다.
- 파일별 `language`는 `detect_language`로 계산해 프론트 구문 강조에 쓸 수 있게 했다.

## 비고
- 라우트는 `backend/src/api/router.py`에 `tasks.router` 한 줄만 추가해 등록했다. 서비스 의존성(`get_task_service`, `get_code_upload_service`)은 `dependencies.py`에 추가했다.
- 다운로드 엔드포인트(`/code/download`, addendum)는 이 태스크 범위가 아니다.
