# TASK-044. ProjectService (생성, 조회, 수정, 소프트 삭제)

## 상태
완료

## 날짜
2026-11-10

## 작업 요약
프로젝트를 만들고, 찾고, 고치고, 지우는 **업무 담당자**(`ProjectService`)를 만들었다. T043의 `Project` 모델이 "물품 목록표"였다면, 이번에는 그 목록표를 보고 실제로 물건을 넣고 빼는 **창고 직원**이다. API 화면(라우터)은 이 직원에게 일을 시키기만 하고, 규칙은 모두 직원이 지킨다.

| 메서드 | 하는 일 |
|--------|---------|
| `create(user_id, title, description=None)` | 새 프로젝트 저장. 제목 앞뒤 공백 제거, 1~255자 검사. 빈 설명은 `None`으로 저장 |
| `get(project_id)` | 사용 중(`active`) 프로젝트 1개 조회. 없거나 휴지통에 있으면 `None` |
| `update(project_id, *, title, description)` | 보낸 항목만 수정. 설명을 `None`으로 보내면 설명 삭제, 아예 안 보내면 그대로 |
| `soft_delete(project_id)` | 휴지통으로 이동. `trashed_at`=지금, `scheduled_deletion_at`=지금+30일. 행은 지우지 않음 |

잘못된 제목은 `400 validation_error`(`details.field = "title"`), 없거나 휴지통에 있는 프로젝트의 수정/삭제는 `404`로 응답한다.

## 변경 파일
- `backend/src/services/project_service.py` (신규): `ProjectService`, 상수 `MAX_TITLE_LENGTH`(255), `TRASH_RETENTION_DAYS`(30)
- `backend/tests/unit/test_project_service.py` (신규): 단위 26개(세션 목 사용)
- `backend/tests/integration/test_project_service_integration.py` (신규): 실제 PostgreSQL 통합 7개
- `specs/001-ai-code-learning-platform/tasks.md`: T044 완료 표시
- `docs/task-reports/TASK-044-ProjectService-생성-조회-수정-소프트삭제.md` (신규): 이 보고서

## TDD 결과
- RED 커밋: 해당 없음(Git 저장소 아님). 구현 전 두 테스트 파일 모두 `ModuleNotFoundError: No module named 'src.services.project_service'`로 실패하는 것을 확인했다.
- GREEN 커밋: 해당 없음. 구현 후 단위 26개 통과. 통합 7개는 DB가 꺼져 있어 처음에는 건너뛰어졌고(skip), DB를 띄운 뒤 실행해 아래 오류 2건을 고친 후 모두 통과했다. 전체 백엔드 392개 통과(기존 359개 + 신규 33개), 기존 테스트는 수정하지 않았다.
- REFACTOR 커밋: 해당 없음. 구현이 이미 간결해 변경하지 않았다.
- 테스트 커버리지: `project_service.py` 100%. 신규 테스트만 돌렸을 때 전체 평균은 30%지만, 이는 다른 모듈을 실행하지 않아서이며 전체 스위트 기준 값은 아니다.
- 정적 검사: ruff, black, mypy(strict) 모두 통과(프로젝트 venv의 `python -m black/mypy` 기준).
- 테스트 작성 중 제 테스트 오류를 바로잡았다(구현 문제가 아님): (1) 통합 테스트에서 `expire_all()` 뒤에 `created.id`를 읽어 비동기 지연 로딩 오류(`MissingGreenlet`)가 났다 → id를 미리 변수에 담도록 수정(T043과 같은 유형). (2) "수정하면 `updated_at`이 커진다"는 단언은 성립할 수 없었다. PostgreSQL의 `now()`는 **트랜잭션 시작 시각**이라 한 트랜잭션 안에서는 생성 시각과 같다. `updated_at` 갱신은 T043 모델의 책임이라 이 태스크 테스트에서 뺐다. (3) 단위 테스트의 항상 참인 단언 두 곳(`or` 조건, MagicMock에 대한 `hasattr`)을 의미 있는 검사로 교체했다.

## 기술 결정
- **휴지통 프로젝트는 서비스에서 "없는 것"으로 취급**: `get`이 `deletion_status = 'active'`만 조회하므로 `update`/`soft_delete`도 휴지통 프로젝트에는 404가 난다. 이미 휴지통에 있는 프로젝트를 다시 삭제하면 `trashed_at`과 30일 기한이 새로 덮어써지는 사고를 막는다. 휴지통 조회/복원은 휴지통 기능(T170~)이 별도로 다룬다.
- **PATCH 의미를 위한 `UNSET` 표식**: "필드를 안 보냄"과 "null로 보냄(설명 지우기)"을 구분해야 한다. `None`을 기본값으로 쓰면 둘을 구별할 수 없어 단일 값 enum(`UNSET`)을 썼다. mypy strict에서 타입이 정확히 좁혀진다.
- **검증을 서비스에 둠**: 제목 공백 제거와 1~255자 검사는 DB 제약(`title_min_length`, VARCHAR(255))에 닿기 전에 서비스가 한국어 메시지로 막는다. 공백만 있는 제목은 DB 제약(`char_length >= 1`)으로는 통과해 버리므로 서비스 검사가 꼭 필요하다. 수정 시에는 검증을 엔티티 변경 전에 끝내 "일부만 바뀐 상태"가 남지 않게 했다.
- **`UserService`와 같은 트랜잭션 규칙**: 서비스는 `flush()`만 하고, 커밋/롤백은 요청 단위 세션(`get_session`)이 맡는다.
- **`delete` 대신 `soft_delete`, 반환값 없음**: 명세가 소프트 삭제(휴지통 30일 보관)이므로 이름에서 드러나게 했다.

## 비고
- **소유권 검증은 이 태스크에 없다.** `get`/`update`/`soft_delete`는 `project_id`만으로 동작하므로, 지금 상태 그대로 API에 연결하면 다른 사용자의 프로젝트도 접근할 수 있다. T045(소유권 검증)가 `user_id` 검사를 얹은 뒤 T046~T050 엔드포인트를 연결해야 한다.
- 프로젝트 **목록 조회**는 T044 범위(생성/조회/수정/소프트 삭제)에 없다. T046(GET /projects)에서 필요하면 추가한다.
- "프로젝트를 삭제하면 하위 태스크도 휴지통으로" 규칙은 Task 모델이 생긴 뒤(T068)에 `soft_delete`에 연결한다. 현재는 프로젝트 행만 휴지통으로 간다.
- 통합 테스트를 실행하려고 Docker Desktop을 켜고 `docker compose up -d db`로 PostgreSQL 컨테이너(`1027_speckit-db-1`)를 띄웠다. 계속 실행 중이다.
- Git 저장소가 아니라 커밋은 없다.
