# TASK-043. Project SQLAlchemy 모델 (소프트 삭제 필드 포함)

## 상태
완료

## 날짜
2026-11-09

## 작업 요약
"프로젝트"를 파이썬 코드에서 다룰 수 있게 하는 설계도(`Project` 모델)를 만들었다. 프로젝트는 학습 태스크들을 담는 **폴더**다. 이미 DB(창고)에는 `projects` 선반이 만들어져 있었고(T009), 이번에는 코드 쪽에서 그 선반의 칸 구성과 똑같은 "물품 목록표"를 만든 셈이다. 칸 구성이 다르면 나중에 물건을 넣다가 터지므로, 실제 DB에 넣어 보는 테스트로 일치를 확인했다.

핵심은 **소프트 삭제**다. 프로젝트를 지워도 바로 버리지 않고 "휴지통" 표시만 한다.

| 칸(컬럼) | 의미 |
|----------|------|
| `deletion_status` | `active`(사용 중) 또는 `trashed`(휴지통). 기본값 `active` |
| `trashed_at` | 휴지통에 넣은 시각 |
| `scheduled_deletion_at` | 영구 삭제 예정 시각(휴지통에 넣은 날 + 30일) |
| `last_activity_at` | 마지막 태스크 활동 시각(태스크가 바뀔 때 갱신, 이후 태스크 서비스가 담당) |

`title`은 1자 이상이어야 하고(빈 제목은 DB가 거부), `deletion_status`는 두 값 외에는 DB가 거부한다. 사용자를 삭제하면 그 사용자의 프로젝트도 DB가 함께 지운다. `User.projects`로 사용자의 프로젝트 목록을, `Project.user`로 주인을 찾을 수 있다.

## 변경 파일
- `backend/src/models/project.py` (신규): `Project` 모델, 상태 상수 `Project.ACTIVE`/`Project.TRASHED`
- `backend/src/models/__init__.py`: `Project` 내보내기 추가
- `backend/src/models/user.py`: `projects` 관계 추가(`passive_deletes=True`)
- `backend/tests/unit/test_project_model.py` (신규): 단위 15개 (컬럼, 타입, NULL 허용, FK, 제약 이름, 인덱스, 관계 등)
- `backend/tests/integration/test_project_model_integration.py` (신규): 실제 PostgreSQL 통합 5개
- `specs/001-ai-code-learning-platform/tasks.md`: T043 완료 표시
- `docs/task-reports/TASK-043-Project-SQLAlchemy-모델.md` (신규): 이 보고서

## TDD 결과
- RED 커밋: 해당 없음(Git 저장소 아님). 구현 전 `ImportError: cannot import name 'Project'`로 두 테스트 파일이 모두 실패하는 것을 확인했다.
- GREEN 커밋: 해당 없음. 구현 후 전체 백엔드 테스트 359개 통과(이 태스크의 새 테스트 20개 포함). 기존 테스트는 수정하지 않았다.
- REFACTOR 커밋: 해당 없음.
- 테스트 작성 중 제 테스트 오류 3건을 바로잡았다(구현 문제가 아님): (1) "저장 전에도 `deletion_status`가 active"라는 기대는 SQLAlchemy 컬럼 기본값이 저장(INSERT) 시점에 적용되는 방식과 맞지 않아 삭제했다. 기본값은 `.default` 검사와 통합 테스트가 확인한다. (2) `repr` 테스트가 저장 전 `None`을 기대하지 못해 명시 값으로 바꿨다. (3) 통합 테스트에서 `expire` 뒤 `project.id`를 읽어 비동기 지연 로딩 오류가 나, 값을 미리 변수에 담도록 고쳤다.
- 커버리지: 백엔드 전체 100% (`project.py` 100%). ruff, black, mypy(strict) 통과.
- 실제 PostgreSQL 확인(통합 테스트): 실제 마이그레이션(001)을 적용한 임시 DB에 ORM으로 저장해 DB 기본값(UUID, 타임스탬프, `active`), 소프트 삭제 필드 왕복, 빈 제목 거부(`title_min_length`), 잘못된 상태값 거부(`projects_deletion_status_check`), 사용자 삭제 시 프로젝트 연쇄 삭제를 확인했다.

## 기술 결정
- **`TimestampMixin` 재사용**: `User`와 같은 관례를 따랐다. 마이그레이션은 `created_at`/`updated_at`을 NULL 허용으로 만들었지만 항상 기본값이 채워지므로 모델에서는 NOT NULL로 다룬다(`User`와 동일). 그래서 `last_activity_at`도 같은 방식으로 맞췄다.
- **제약 이름을 마이그레이션과 같게**: `title_min_length`는 마이그레이션에 이름이 있고, 상태 검사는 이름이 없어 PostgreSQL이 `projects_deletion_status_check`로 자동 부여한다. 이름이 어긋나면 나중에 마이그레이션을 자동 비교할 때 가짜 차이가 생기므로 `conv()`로 똑같이 맞췄다(`User.valid_email`과 같은 방식).
- **부분 인덱스 `idx_projects_user_active`**: `WHERE deletion_status = 'active'` 조건까지 모델에 그대로 선언했다. "내 사용 중 프로젝트 목록" 조회가 가장 잦기 때문이다.
- **상태 상수를 모델에 둠(`Project.ACTIVE`/`TRASHED`)**: 서비스(T044)와 휴지통(T170~)이 `"trashed"` 문자열을 흩어 쓰다 오타 나는 일을 막는다. Enum 타입은 쓰지 않았다. DB가 문자열 + CHECK로 정의돼 있어 마이그레이션을 바꾸지 않기 위해서다.
- **`User.projects`/`Project.user` 양방향 관계 + `passive_deletes=True`**: `RefreshToken`과 같은 방식이다. 사용자 삭제는 DB의 `ON DELETE CASCADE`에 맡긴다. `Project.tasks` 관계는 Task 모델(T061)이 만들어질 때 함께 추가한다.

## 비고
- 모델만 추가했으므로 **새 마이그레이션은 없다**. 개발 DB(`codelearning`)는 그대로 쓰면 된다.
- 실행 중인 백엔드(8000)는 이 모델을 아직 쓰는 곳이 없어 영향이 없다.
- 다음 태스크 T044(`ProjectService`: 생성, 조회, 수정, 소프트 삭제)가 이 모델을 사용한다. 소프트 삭제 시 `trashed_at`과 `scheduled_deletion_at = trashed_at + 30일`을 함께 기록해야 하고, "프로젝트를 삭제하면 하위 태스크도 휴지통으로" 규칙은 Task 모델이 생긴 뒤(T068) 연결해야 한다.
- Git 저장소가 아니라 커밋은 없다.
