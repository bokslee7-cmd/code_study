# TASK-049. PATCH /projects/{project_id} (프로젝트 수정 API)

## 상태
완료

## 날짜
2026-11-10

## 작업 요약
"이 상자의 이름표만 바꿔 주세요"라는 **수정 창구**(`PATCH /api/v1/projects/{project_id}`)를 열었다. 이 창구의 핵심은 **"말하지 않은 건 건드리지 않는다"**이다. 손님이 제목만 바꾸겠다고 하면 설명은 그대로 두고, 설명을 `null`로 보내면 "설명을 지워 달라"는 뜻으로 받아들인다. 창고 직원(`ProjectService.update`)은 이 구분을 위해 이미 "안 보냄"(`UNSET`)과 "비움"(`None`)을 따로 취급하도록 만들어져 있었고, 이번 작업은 창구가 손님의 말을 그대로 전달하게 연결한 것이다.

| 요청 본문 | 결과 |
|-----------|------|
| `{"title": "새 제목"}` | 제목만 변경, 설명 유지 |
| `{"description": "새 설명"}` | 설명만 변경, 제목 유지 |
| `{"description": null}` | 설명 삭제(`null`로 저장), 제목 유지 |
| `{"title": "...", "description": "..."}` | 둘 다 변경 |
| `{}` | 변경 없음. 그래도 소유권/존재 검사는 수행, `200` |
| `{"title": null}` | `400 validation_error` (제목은 `null` 불가) |
| `title`/`description`이 문자열이 아님 | `400 validation_error` |
| 제목이 공백뿐이거나 255자 초과 | `400 validation_error`, `details.field = "title"` (서비스 판정) |
| 남의 프로젝트 | `403 forbidden` |
| 없음 / 휴지통 | `404 not_found` |
| `project_id`가 UUID 아님 | `400 validation_error` |
| 로그인 안 함 | `401 unauthorized` |

성공 시 `200` + `ProjectResponse`.

## 변경 파일
- `backend/src/api/projects.py`: `PATCH /projects/{project_id}` 추가
- `backend/src/api/schemas/project.py`: 요청 스키마 `ProjectUpdate` 추가(`title`이 `null`이면 거부하는 검증 포함)
- `backend/tests/unit/test_projects_api.py`: 수정 API 테스트 15개 추가(총 42개), 배선 테스트에 `PATCH` 경로 확인 추가
- `docs/task-reports/TASK-049-PATCH-projects-id-프로젝트-수정-API.md` (신규): 이 보고서

## TDD 결과
- RED 커밋: 해당 없음(Git 저장소 아님). 구현 전 테스트를 실행해 **16개 실패**를 확인했다(PATCH 경로 미등록).
- GREEN 커밋: 해당 없음. 구현 후 `test_projects_api.py` 42개 통과. 전체 백엔드 **447개 통과**(T048 시점 432 + 신규 15).
- REFACTOR 커밋: 해당 없음.
- 테스트 커버리지: 백엔드 전체 100%(744줄 중 누락 0).
- 정적 검사: ruff, black, mypy(strict) 모두 종료 코드 0(프로젝트 venv의 `python -m` 기준).

## 기술 결정
- **"보냈는가"를 pydantic의 `model_dump(exclude_unset=True)`로 판별**: 클라이언트가 실제로 보낸 필드만 서비스의 키워드 인자로 전달한다. 안 보낸 필드는 서비스에서 `UNSET` 기본값이 그대로 적용되어 유지된다. 라우터에 `if title is not None` 같은 분기를 두지 않아 "null 보냄"과 "안 보냄"이 섞이지 않는다. 테스트는 `assert_awaited_once_with(project_id, USER_ID, title="새 제목")`처럼 **안 보낸 인자가 전달되지 않았음**까지 정확히 확인한다.
- **`title: null`은 스키마에서 400 처리**: 스키마의 `title`은 `str | None = None`이지만, 필드 검증기가 "보냈는데 `null`"인 경우만 거부한다(기본값은 검증 대상이 아니라 안 보낸 경우는 통과). 서비스의 `title` 타입(`str | _Unset`)에 `None`이 들어가 `.strip()` 오류(500)가 나는 것을 막는다. 오류 메시지는 한국어로 두었다.
- **빈 본문 `{}`도 200**: 서비스가 소유권/존재를 먼저 확인한 뒤 아무것도 바꾸지 않고 현재 프로젝트를 돌려준다. 계약에 "빈 본문은 오류"라는 규정이 없고, 에러로 만들면 규칙이 하나 더 생긴다(YAGNI).
- **소유권 검사 → 입력 검증 순서 유지**: 남의 프로젝트에 공백 제목을 보내면 400이 아니라 403이다(T045 결정). 단 `null`/타입 오류처럼 스키마 단계에서 걸리는 것은 서비스 호출 전이므로 400이다.

## 비고
- 한계: 스키마 단계의 400(`title: null`, 타입 오류)은 소유권 검사보다 먼저 일어나므로, 남의 프로젝트에도 형식이 틀린 본문은 400을 받는다. 형식 검증은 권한과 무관한 정보만 노출하므로 허용했다.
- 서비스 `update`가 `updated_at`을 갱신하는지는 T043 모델(`onupdate=func.now()`)의 책임이다.
- Git 저장소가 아니라 커밋은 없다.
