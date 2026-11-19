# TASK-050. DELETE /projects/{project_id} (프로젝트 소프트 삭제 API)

## 상태
완료

## 날짜
2026-11-10

## 작업 요약
"이 상자 치워 주세요"라는 **폐기 창구**(`DELETE /api/v1/projects/{project_id}`)를 열었다. 다만 상자를 쓰레기통에 던지는 게 아니라 **휴지통 칸으로 옮겨 30일간 보관**한다(소프트 삭제). 실제 이동은 `ProjectService.soft_delete`가 하고, 창구는 "누구의 요청인지"를 전달만 한다. 이로써 T046~T050의 5개 엔드포인트가 모두 갖춰졌다.

| 상황 | 응답 |
|------|------|
| 내 프로젝트 | `204 No Content` (본문 없음). 목록에서 사라지고 휴지통 상태로 DB에 남음 |
| 다른 사용자의 프로젝트 | `403 forbidden` (아무것도 바뀌지 않음) |
| 없음 / 이미 휴지통 | `404 not_found` |
| `project_id`가 UUID 아님 | `400 validation_error` |
| 로그인 안 함 | `401 unauthorized` |

이번 태스크에서는 **실제 PostgreSQL 통합 테스트**도 추가해, 앞선 T046~T049까지 포함한 전체 흐름을 진짜 서버 조립(실제 `get_session`의 커밋/롤백 포함)과 실제 DB로 확인했다.

| 통합 시나리오 | 확인한 것 |
|---------------|-----------|
| 내 프로젝트만 보임 / 남의 것 403 | 두 사용자가 각각 프로젝트 생성 → 목록에는 본인 것만. 남의 프로젝트 조회/수정/삭제는 모두 403이고 남의 데이터는 그대로 |
| 삭제 후 목록에서 사라짐 | `204` → 목록에서 제외, 상세 `404`, 다시 삭제 `404`. DB 행은 남아 있고 `deletion_status='trashed'`, `trashed_at` 기록됨 |
| PATCH 의미 | 제목만 보내면 설명 유지, `description: null`이면 설명 삭제, 이후 조회에도 반영 |
| 목록 정렬 | `last_activity_at` 내림차순이 실제 DB 쿼리로 동작 |

## 변경 파일
- `backend/src/api/projects.py`: `DELETE /projects/{project_id}` 추가(`status_code=204`)
- `backend/tests/unit/test_projects_api.py`: 삭제 API 테스트 6개 추가(총 48개), 배선 테스트에 `DELETE` 경로 확인 추가
- `backend/tests/integration/test_projects_api_integration.py` (신규): 실제 PostgreSQL 통합 테스트 4개(임시 DB 생성 → 마이그레이션 → 테스트 후 삭제, 개발 DB `codelearning`은 건드리지 않음)
- `docs/task-reports/TASK-050-DELETE-projects-id-프로젝트-삭제-API.md` (신규): 이 보고서

## TDD 결과
- RED 커밋: 해당 없음(Git 저장소 아님). 구현 전 단위 테스트를 실행해 **7개 실패**를 확인했다(DELETE 경로 미등록).
- GREEN 커밋: 해당 없음. 구현 후 `test_projects_api.py` 48개 통과. 통합 테스트 4개는 이미 구현된 T046~T050 위에 작성한 **종단 간 검증**이라 처음부터 통과했다(RED 없음). 대신 "테스트가 정말 잘못을 잡는가"를 확인하려고 `get_user_projects`의 소유자 필터를 임시로 제거했더니 "내 것만 보임" 통합 테스트가 실패했고, 원복 후 통과했다.
- REFACTOR 커밋: 해당 없음.
- 전체 결과: 백엔드 **457개 통과**(T049 시점 447 + 단위 6 + 통합 4). `pytest` 종료 코드 0.
- 테스트 커버리지: 백엔드 전체 **100%**(747줄 중 누락 0).
- 정적 검사: `ruff check src tests`, `black --check src tests`, `mypy src`(strict) 모두 종료 코드 0(프로젝트 venv의 `python -m` 기준).
- 작업 중 문제 1건: 통합 테스트의 한글이 든 긴 단언에서 ruff E501(black은 통과)이 났다. 알려진 한글 폭 차이라서 응답에서 `(title, description)` 쌍을 뽑는 작은 함수로 나눠 해결했다. 테스트가 검증하는 값은 같다.
- 정리 확인: 테스트 종료 후 임시 DB(`projects_api_*`, `project_service_*`)가 남아 있지 않음을 확인했다.

## 기술 결정
- **204는 본문 없이**: FastAPI에서 `status_code=204`로 선언하고 `None`을 반환한다. 테스트가 응답 본문이 정확히 비어 있는지(`b""`) 확인한다. 이미 휴지통인 프로젝트를 다시 지우면 멱등 `204`가 아니라 `404`다(계약과 T044 결정: `trashed_at`/30일 기한이 새로 덮어써지는 사고 방지).
- **통합 테스트는 실제 `get_session`을 사용**: 세션 의존성을 직접 바꿔치기하지 않고 `get_session_factory`만 임시 DB용으로 교체했다. 그래서 요청이 성공하면 커밋, 실패하면 롤백되는 실제 경로까지 같이 검증된다. HTTP 호출은 `httpx.ASGITransport`로 서버 프로세스 없이 앱을 직접 호출한다.
- **통합 테스트를 소수 시나리오로**: 규칙별 케이스는 단위 테스트(48개)가 이미 촘촘히 확인한다. 통합 테스트는 "여러 계층이 실제로 맞물리는가"에 집중해 4개로 제한했다(속도: 임시 DB 생성과 마이그레이션에 테스트당 수 초).
- **"하위 태스크도 휴지통으로" 규칙은 아직 없음**: Task 모델이 없으므로 T068 이후에 `soft_delete`에 연결한다(T044 보고서와 동일).

## 비고
- 이 태스크로 `/api/v1/projects` 5개 엔드포인트가 계약대로 완성됐다. 프론트엔드와 합의한 계약에서 **벗어난 부분은 없다.**
- 응답의 `task_count`, `completed_task_count`, `progress_percent`는 0 고정이며 T068 이후 실제 집계로 교체해야 한다(스키마 `ProjectResponse`의 주석 참고).
- 통합 테스트 파일의 임시 DB 생성/마이그레이션 픽스처가 `test_project_service_integration.py`와 거의 같다. 세 번째로 필요해지면 `conftest.py`로 모으는 리팩터링을 권장한다(지금은 두 번째라 합치지 않았다).
- `tasks.md`는 지시에 따라 수정하지 않았다(오케스트레이터가 T046~T050 완료 표시 예정).
- Git 저장소가 아니라 커밋은 없다.
