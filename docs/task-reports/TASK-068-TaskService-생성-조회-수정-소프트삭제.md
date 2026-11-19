# TASK-068. TaskService 생성 조회 수정 소프트삭제

## 상태
완료

## 날짜
2026-11-16

## 작업 요약
태스크 CRUD 서비스. 모든 메서드가 사용자 ID를 받아 프로젝트 소유권을 검사한다.

| 메서드 | 동작 |
|--------|------|
| `create(user_id, project_id, title, description, upload_method)` | 프로젝트 소유권 확인 후 `task_number = max + 1`로 생성 |
| `list_for_project(project_id, user_id)` | 활성 태스크를 `task_number` 오름차순으로 반환 |
| `get_owned(task_id, user_id)` | 없거나 휴지통이면 404, 남의 프로젝트면 403 |
| `update(task_id, user_id, title=, description=)` | 보낸 필드만 수정(`UNSET` 의미 구분), `description=None`은 삭제 |
| `soft_delete(task_id, user_id)` | `trashed`, `trashed_at`, `scheduled_deletion_at = +30일` |

검증: 제목 5~255자(FR-008), 설명 최대 500자(FR-009, 빈 값은 None), `upload_method`는 file/folder/paste 또는 None. 실패는 `AppError(400, validation_error, details={field})`.

## 변경 파일
- `backend/src/services/task_service.py` (신규)
- `backend/tests/unit/test_task_service.py` (신규, 38개)
- `backend/tests/integration/test_task_service_integration.py` (신규, 4개, DB 필요로 skip)
- `specs/001-ai-code-learning-platform/tasks.md` (T068 완료 표시)

## TDD 결과
- RED: 구현 전 테스트를 먼저 작성하고 실행해 수집 단계 오류(모듈/라우트 부재)로 실패함을 확인함
- GREEN: 최소 구현 후 통과 확인
- REFACTOR: black / ruff / mypy 통과 확인
- 전체 백엔드: 736 passed, 47 skipped (이전 608 passed, 43 skipped). skipped는 PostgreSQL이 필요한 통합 테스트로, 이 환경에 DB가 없어 실행되지 않음
- 커밋: Git 저장소가 아니라 없음
- 커버리지: `task_service.py` 100%
- 이 태스크 테스트: 단위 38개 통과, 통합 4개 skipped(작성만 하고 실행하지 못함)

## 기술 결정
- 번호 부여: `max(task_number)+1`을 휴지통 태스크까지 포함해 계산한다(번호는 불변이며 재사용하지 않음, FR-004). 동시 생성 시 같은 번호를 읽지 않도록 프로젝트 행을 `refresh(with_for_update=True)`로 잠근 뒤 계산한다. `(project_id, task_number)` UNIQUE 제약이 최후 방어선이다.
- 수정 필드에 `task_number`가 없으므로 불변이다.
- 생성/수정/삭제 시 `project.last_activity_at`을 갱신한다(data-model: 태스크 변경 시 갱신).
- `update`/`create`에서 `refresh(task, [타임스탬프 컬럼])`를 호출한다. 비동기 세션에서 `onupdate` 값에 접근하면 lazy load로 오류가 나기 때문이다(ProjectService와 같은 이유).
- 응답에 쓰는 `uploaded_code`는 `selectinload`로 미리 읽는다.

## 비고
- 미해결: `ProjectService.soft_delete`의 "하위 태스크도 함께 휴지통으로" 동작(FR-009D)과 `ProjectResponse.task_count/completed_task_count/progress_percent` 실제 집계는 T068 범위에 없어 건드리지 않았다(주석상 후속). 프로젝트가 휴지통에 가면 태스크는 `active`로 남지만 소유권 검사가 404를 내므로 접근은 막힌다. 휴지통 기능(T170+)에서 처리 필요.
- 통합 테스트는 PostgreSQL이 있는 환경에서 한 번 실행해 확인해야 한다(행 잠금, selectinload, 백릴레이션 설정 검증).
