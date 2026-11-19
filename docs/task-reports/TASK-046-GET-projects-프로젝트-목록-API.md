# TASK-046. GET /projects (프로젝트 목록 조회 API)

## 상태
완료

## 날짜
2026-11-10

## 작업 요약
"내 프로젝트 목록 보여 주세요"라는 **창구**(`GET /api/v1/projects`)를 처음 열었다. T044~T045에서 만든 창고 직원(`ProjectService`)에게 "이 손님 상자 목록 가져와"라고 시키고, 받은 상자를 화면(프론트엔드)이 읽기 좋은 형식으로 포장해 내보내는 것까지만 창구가 한다. 규칙은 모두 직원이 지킨다.

| 항목 | 내용 |
|------|------|
| 경로 | `GET /api/v1/projects` (로그인 필수, `Authorization: Bearer <access token>`) |
| 응답 | `200 {"projects": [ProjectResponse, ...]}` |
| 보이는 범위 | **본인의** `active` 프로젝트만. 휴지통에 간 것과 남의 것은 안 나옴 |
| 정렬 | `last_activity_at` 내림차순 → 같으면 `created_at` 내림차순 (최근 활동한 것이 위) |
| 로그인 안 함 | `401 unauthorized` (서비스 호출 없음) |

`ProjectResponse` 필드: `id`, `title`, `description`(없으면 `null`), `created_at`, `updated_at`, `last_activity_at`, `task_count`, `completed_task_count`, `progress_percent`.
- 휴지통 관련 필드(`deletion_status`, `trashed_at`, `scheduled_deletion_at`)와 `user_id`는 **응답에 넣지 않았다**(프론트와 합의한 계약).
- Task 모델이 아직 없어서 세 개의 카운트(`task_count`, `completed_task_count`, `progress_percent`)는 **0 고정**이다. 스키마 파일에 "T068 이후 실제 집계로 교체" 주석을 남겼다.

## 변경 파일
- `backend/src/api/projects.py` (신규): `GET /projects` 라우터(요청 받기 → 서비스 호출 → 응답 변환만 수행)
- `backend/src/api/schemas/project.py` (신규): `ProjectResponse`, `ProjectListResponse`
- `backend/src/api/dependencies.py`: `get_project_service` 추가(`get_user_service`와 같은 방식)
- `backend/src/api/router.py`: `create_api_router()`에 `projects.router` 등록
- `backend/src/services/project_service.py`: `get_user_projects(user_id) -> list[Project]` 추가
- `backend/tests/unit/test_project_service.py`: 목록 조회 단위 테스트 4개 추가
- `backend/tests/unit/test_projects_api.py` (신규): API 계약 테스트 8개(배선 2 + 목록 6)
- `docs/task-reports/TASK-046-GET-projects-프로젝트-목록-API.md` (신규): 이 보고서

## TDD 결과
- RED 커밋: 해당 없음(Git 저장소 아님). 구현 전에 테스트를 먼저 쓰고 실행했다. 서비스 테스트는 `get_user_projects` 없음으로 **4개 실패**, API 테스트 파일은 `ImportError: cannot import name 'get_project_service'`로 수집 단계에서 실패했다.
- GREEN 커밋: 해당 없음. 구현 후 대상 테스트 53개(서비스 37 + API 8 + 라우터 8) 통과. 전체 백엔드 **413개 통과**(기존 401 + 신규 12).
- REFACTOR 커밋: 해당 없음. 테스트에서 `or`로 두 경우를 허용하던 약한 단언 하나를 정확한 단언으로 바꿨다(UUID가 SQL에 하이픈 없이 들어가는 것을 직접 확인).
- 테스트 커버리지: 백엔드 전체 100%(719줄 중 누락 0), `projects.py`·`dependencies.py`·`project_service.py` 모두 100%.
- 정적 검사: ruff, black, mypy(strict) 모두 통과(프로젝트 venv의 `python -m` 기준).

## 기술 결정
- **목록 정렬을 DB에서 처리**: `ORDER BY last_activity_at DESC, created_at DESC`를 쿼리에 넣었다. 파이썬에서 다시 정렬하면 프로젝트가 많아질수록 느려지고, 기존 `idx_projects_user_active` 인덱스가 사용자별 조회를 받쳐 준다.
- **서비스가 `list`를 돌려줌**: SQLAlchemy의 결과 객체를 그대로 넘기지 않고 `list`로 바꿔 API가 DB 세부사항을 몰라도 되게 했다.
- **카운트 0 고정은 스키마 기본값으로**: 라우터에 `0`을 하드코딩하지 않고 `ProjectResponse` 필드 기본값으로 뒀다. 나중에 집계가 생기면 서비스가 값을 채워 주고 스키마 한 곳만 고치면 된다.
- **목록은 소유권 검사 불필요**: `WHERE user_id = :나`로 자기 것만 조회하므로 T045의 `get_owned`를 쓰지 않는다.

## 비고
- 프로젝트 수가 많아질 때의 페이지네이션은 이번 계약에 없어 만들지 않았다(YAGNI).
- 이 단계의 단위 API 테스트는 서비스를 목(mock)으로 바꾼 것이라 실제 DB 동작("내 것만 보임", "삭제 후 사라짐")은 T050 단계에서 PostgreSQL 통합 테스트로 확인한다.
- Git 저장소가 아니라 커밋은 없다.
