# TASK-047. POST /projects (프로젝트 생성 API)

## 상태
완료

## 날짜
2026-11-10

## 작업 요약
"새 프로젝트 하나 만들어 주세요"라는 **접수 창구**(`POST /api/v1/projects`)를 열었다. 창구는 신청서(JSON)를 받아 형식만 확인하고, 접수 처리(제목 다듬기, 길이 검사, 저장)는 창고 직원(`ProjectService.create`)에게 맡긴다. 신청서에 적힌 주인이 아니라 **로그인한 사람**이 항상 주인으로 등록된다.

| 항목 | 내용 |
|------|------|
| 경로 | `POST /api/v1/projects` (로그인 필수) |
| 요청 본문 | `{"title": str, "description"?: str \| null}` |
| 성공 | `201` + `ProjectResponse` (T046과 같은 형식. 카운트 3개는 0) |
| 제목이 공백뿐이거나 255자 초과 | `400 validation_error`, `details.field = "title"` (서비스가 판정) |
| 본문 누락/타입 오류 (`{}`, `title: null`, `title: 1`, `description: 1`, 본문 없음) | `400 validation_error` (기존 공통 핸들러) |
| 로그인 안 함 | `401 unauthorized` (서비스 호출 없음) |

## 변경 파일
- `backend/src/api/projects.py`: `POST /projects` 추가(요청 변환 → `create` 호출 → 응답 변환)
- `backend/src/api/schemas/project.py`: 요청 스키마 `ProjectCreate` 추가
- `backend/tests/unit/test_projects_api.py`: 생성 API 테스트 13개 추가(총 21개), 배선 테스트에 `POST` 경로 확인 추가
- `docs/task-reports/TASK-047-POST-projects-프로젝트-생성-API.md` (신규): 이 보고서

## TDD 결과
- RED 커밋: 해당 없음(Git 저장소 아님). 구현 전 테스트 작성 후 실행해 **14개 실패**를 확인했다(POST 경로가 없어 405/배선 불일치).
- GREEN 커밋: 해당 없음. 구현 후 `test_projects_api.py` 21개 모두 통과. 전체 백엔드 **426개 통과**(T046 시점 413 + 신규 13).
- REFACTOR 커밋: 해당 없음.
- 테스트 커버리지: 백엔드 전체 100%(726줄 중 누락 0).
- 정적 검사: ruff, black, mypy(strict) 모두 종료 코드 0(프로젝트 venv의 `python -m` 기준).
- 작업 중 문제 1건: 테스트 파일의 한글이 든 긴 줄에서 ruff E501이 났다(black은 통과). 알려진 한글 폭 계산 차이라서 해당 테스트 값을 영문(`"desc"`)으로 바꿔 해결했다. 검증하려는 동작(설명만 있고 제목이 없는 본문)은 같다.

## 기술 결정
- **주인은 토큰에서만 정함**: 본문에 `user_id`를 보내도 스키마에 없는 필드라 무시되고, 서비스에는 `CurrentUser.id`가 전달된다. "남의 이름으로 프로젝트 만들기"를 테스트로 막아 두었다.
- **제목 검증은 서비스에만**: 스키마는 `title: str`(null/숫자 거부)까지만 보고, 공백 제거와 1~255자 검사는 서비스가 한다. 규칙이 두 곳에 있으면 어긋나므로 한 곳으로 모았다.
- **서비스 에러는 그대로 통과**: 서비스가 던진 `AppError`는 기존 핸들러가 `{error, message, details}` 형식으로 변환한다. 라우터에 `try/except`를 두지 않았다.

## 비고
- 응답의 `task_count` 등 3개 카운트는 새 프로젝트이므로 0이 정확한 값이다(Task 모델은 T068 이후).
- Git 저장소가 아니라 커밋은 없다.
