# TASK-045. 프로젝트 소유권 검증

## 상태
완료

## 날짜
2026-11-10

## 작업 요약
"내 프로젝트만 내가 보고, 고치고, 지울 수 있게" 하는 **출입 확인**을 `ProjectService`에 넣었다. T044의 창고 직원은 "몇 번 상자 지워 주세요"라는 말만 들으면 누구의 상자인지 묻지 않고 지웠다. 이제는 요청자의 신분(`user_id`)을 함께 받아 상자 주인과 비교한다.

| 상황 | 응답 |
|------|------|
| 내 프로젝트 | 정상 처리 |
| 다른 사용자의 프로젝트 | `403 forbidden` — "이 프로젝트에 접근할 권한이 없습니다." |
| 없는 프로젝트 / 휴지통에 있는 프로젝트 | `404 not_found` — "요청한 프로젝트를 찾을 수 없습니다. 삭제되었거나 존재하지 않는 프로젝트입니다." |

메시지는 `requirements-addendum.md`의 에러 카테고리(403/404 문구)를 그대로 따랐다.

서비스 변경점:
- **`get_owned(project_id, user_id)` 신설**: 위 표대로 판정하고 프로젝트를 돌려준다. `GET /projects/{id}`(T048)가 사용한다.
- **`update(project_id, user_id, *, ...)`, `soft_delete(project_id, user_id)`**: `user_id`가 필수 인자가 됐고, 내부에서 `get_owned`를 거친다. 검사를 빠뜨리고 호출하는 것이 불가능하다.
- `get(project_id)`는 소유권을 보지 않는 단순 조회로 남겼다(독스트링에 명시).

## 변경 파일
- `backend/src/services/project_service.py`: `get_owned` 추가, `update`/`soft_delete`에 `user_id` 추가, 메시지 상수(`PROJECT_NOT_FOUND_MESSAGE`, `PROJECT_FORBIDDEN_MESSAGE`), 쓰지 않게 된 `_get_or_raise` 제거
- `backend/tests/unit/test_project_service.py`: T044 호출부를 새 시그니처로 수정 + 소유권 단위 테스트 7개 추가(총 33개)
- `backend/tests/integration/test_project_service_integration.py`: 호출부 수정 + 실제 PostgreSQL 소유권 테스트 2개 추가(총 9개)
- `specs/001-ai-code-learning-platform/tasks.md`: T045 완료 표시
- `docs/task-reports/TASK-045-프로젝트-소유권-검증.md` (신규): 이 보고서

## TDD 결과
- RED 커밋: 해당 없음(Git 저장소 아님). 호출부를 새 시그니처로 바꾸고 소유권 테스트를 추가한 뒤 실행해 **26개 실패**를 확인했다(`update`/`soft_delete`가 `user_id`를 받지 않음, `get_owned` 없음).
- GREEN 커밋: 해당 없음. 구현 후 프로젝트 테스트 42개 통과, 전체 백엔드 401개 통과(T044 시점 392개 + 신규 9개). 기존 테스트는 호출 시그니처만 맞췄고 검증 내용은 바꾸지 않았다.
- REFACTOR 커밋: 해당 없음. 쓰지 않게 된 `_get_or_raise`를 제거했다.
- 테스트 커버리지: 백엔드 전체 100%, `project_service.py` 100%.
- 정적 검사: ruff, black, mypy(strict) 모두 종료 코드 0(프로젝트 venv의 `python -m` 기준).
- 실제 PostgreSQL 확인(통합 테스트): 다른 사용자가 `get_owned`/`update`/`soft_delete`를 시도하면 모두 403이고, DB 행(제목, 설명, 상태, `trashed_at`)이 그대로임을 확인했다. 휴지통 프로젝트는 다른 사용자에게도 404다.
- 작업 중 문제 2건: (1) 처음에 테스트 추가를 잘못된 경로(cwd가 `backend/tests`)로 해서 아무것도 추가되지 않았는데 `echo ok`만 출력돼 성공처럼 보였다. 파일 끝을 직접 확인해 발견하고 다시 추가했다. (2) 404 메시지가 길어 ruff E501(줄 길이)이 나왔다. black은 한 줄로 합치고 ruff는 한글 폭 때문에 거부하는 충돌이라, 문장을 두 상수로 나눠 f-string으로 합쳤다.

## 기술 결정
- **`update`/`soft_delete`의 시그니처를 바꿔 `user_id` 필수화(T044 변경)**: 별도 `validate_ownership()`을 만들어 API가 먼저 호출하게 하는 방식도 가능했지만, 호출을 깜빡하면 다른 사람 프로젝트가 수정된다. 필수 인자로 만들면 빠뜨릴 수 없고, 잘못 쓰면 `TypeError`로 바로 드러난다. 아직 이 메서드를 호출하는 API(T046~T050)가 없어 영향 범위는 테스트뿐이었다.
- **존재 확인 → 소유권 확인 순서**: 없거나 휴지통인 프로젝트는 누가 요청하든 404다. 휴지통에 간 프로젝트가 "원래 누구 것이었는지"가 403으로 새어 나가지 않는다.
- **소유권 검사 → 입력 검증 순서**: 남의 프로젝트에 빈 제목을 보내도 400이 아니라 403이다. 권한 없는 사용자에게 검증 규칙을 알려 주지 않는다.
- **403 vs 404**: 명세가 "다른 사용자의 프로젝트는 403"으로 정해 둬서 따랐다. 이 방식은 "그 ID의 프로젝트가 존재한다"는 사실이 드러난다. ID가 UUID라 추측이 사실상 불가능해 위험은 낮다고 판단했다. 존재 자체를 숨기려면 404로 통일해야 하는데, 이는 명세 변경이 필요하므로 이번에는 바꾸지 않았다.
- **`get()`을 남김**: 휴지통/관리 로직이 소유권과 무관한 조회가 필요할 수 있어 제거하지 않았다. 대신 독스트링으로 "사용자 대신 동작할 때는 `get_owned`를 쓸 것"을 명시했다.

## 비고
- API 엔드포인트(T046~T050)는 반드시 `get_owned`/`update`/`soft_delete`에 **인증된 사용자의 id**를 넘겨야 한다. `get()`을 직접 쓰면 소유권 검사가 없다.
- 프로젝트 **목록 조회**(`GET /projects`, T046)는 아직 서비스 메서드가 없다. 목록은 자기 `user_id`로 필터하므로 별도 소유권 검사 없이 `WHERE user_id = :me AND deletion_status = 'active'`로 구현하면 된다.
- 이전 대화에서 만든 임시 시나리오 스크립트(scratchpad)는 `update`/`soft_delete` 시그니처가 바뀌어 그대로는 동작하지 않는다. 프로젝트 코드가 아니라 임시 파일이다.
- PostgreSQL 컨테이너(`1027_speckit-db-1`)는 계속 실행 중이다.
- Git 저장소가 아니라 커밋은 없다.
