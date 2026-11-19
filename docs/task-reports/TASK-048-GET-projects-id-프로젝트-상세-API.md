# TASK-048. GET /projects/{project_id} (프로젝트 상세 조회 API)

## 상태
완료

## 날짜
2026-11-10

## 작업 요약
"이 번호 상자 하나만 꺼내 보여 주세요"라는 **개별 조회 창구**(`GET /api/v1/projects/{project_id}`)를 열었다. 창구는 번호표(UUID)가 올바른 형식인지만 확인하고, "이 상자가 정말 이 손님 것인가"의 판정은 T045에서 만든 `get_owned`에게 맡긴다.

| 상황 | 응답 |
|------|------|
| 내 프로젝트 | `200` + `ProjectResponse` |
| 다른 사용자의 프로젝트 | `403 forbidden` |
| 없는 프로젝트 / 휴지통에 있는 프로젝트 | `404 not_found` |
| `project_id`가 UUID 형식이 아님 | `400 validation_error` (서비스 호출 없음) |
| 로그인 안 함 | `401 unauthorized` (서비스 호출 없음) |

## 변경 파일
- `backend/src/api/projects.py`: `GET /projects/{project_id}` 추가
- `backend/tests/unit/test_projects_api.py`: 상세 조회 테스트 6개 추가(총 27개), 배선 테스트에 경로 확인 추가
- `docs/task-reports/TASK-048-GET-projects-id-프로젝트-상세-API.md` (신규): 이 보고서

## TDD 결과
- RED 커밋: 해당 없음(Git 저장소 아님). 구현 전 테스트를 실행해 **7개 실패**를 확인했다(경로 미등록으로 404).
- GREEN 커밋: 해당 없음. 구현 후 `test_projects_api.py` 27개 통과. 전체 백엔드 **432개 통과**(T047 시점 426 + 신규 6).
- REFACTOR 커밋: 해당 없음.
- 테스트 커버리지: 백엔드 전체 100%(731줄 중 누락 0).
- 정적 검사: ruff, black, mypy(strict) 모두 종료 코드 0(프로젝트 venv의 `python -m` 기준).

## 기술 결정
- **UUID 형식 검사는 FastAPI 타입(`project_id: UUID`)에 맡김**: 잘못된 형식은 라우터 코드가 실행되기 전에 기존 검증 핸들러가 `400`으로 응답한다. 직접 파싱 코드를 쓰지 않아 코드가 짧다.
- **`get()`이 아니라 `get_owned()`만 호출**: T045 보고서의 당부대로 인증된 사용자의 id를 함께 넘긴다. 테스트가 `get_owned(project_id, USER_ID)`로 호출됐는지 직접 확인한다.
- **403/404 판정 순서는 서비스 책임**: "없음/휴지통 → 404, 남의 것 → 403" 순서는 서비스가 정하고 API 테스트는 그 결과가 올바른 HTTP 응답으로 변환되는지만 본다(실제 판정은 T045 통합 테스트가 DB로 확인).

## 비고
- Git 저장소가 아니라 커밋은 없다.
