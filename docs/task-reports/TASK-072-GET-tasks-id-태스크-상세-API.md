# TASK-072. GET tasks id 태스크 상세 API

## 상태
완료

## 날짜
2026-11-16

## 작업 요약
`GET /api/v1/tasks/{task_id}` -> `TaskResponse`(T070과 동일 필드). 오류: 401, 403(남의 프로젝트), 404(없음/휴지통/프로젝트 휴지통).

## 변경 파일
- `backend/src/api/tasks.py`, `backend/tests/unit/test_tasks_api.py` (공용)
- `specs/001-ai-code-learning-platform/tasks.md` (T072 완료 표시)

## TDD 결과
- RED: 구현 전 테스트를 먼저 작성하고 실행해 수집 단계 오류(모듈/라우트 부재)로 실패함을 확인함
- GREEN: 최소 구현 후 통과 확인
- REFACTOR: black / ruff / mypy 통과 확인
- 전체 백엔드: 736 passed, 47 skipped (이전 608 passed, 43 skipped). skipped는 PostgreSQL이 필요한 통합 테스트로, 이 환경에 DB가 없어 실행되지 않음
- 커밋: Git 저장소가 아니라 없음
- 이 엔드포인트 테스트: 정상, 업로드 없는 태스크(`uploaded_code: null`), 404/403

## 기술 결정
- 프로젝트와 같이 존재 여부를 먼저 확인하고 소유권을 검사한다(휴지통 항목의 소유자가 노출되지 않음).

## 비고
- 라우트는 `backend/src/api/router.py`에 `tasks.router` 한 줄만 추가해 등록했다. 서비스 의존성(`get_task_service`, `get_code_upload_service`)은 `dependencies.py`에 추가했다.

