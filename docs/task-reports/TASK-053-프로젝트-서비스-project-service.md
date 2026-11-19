# TASK-053. 프로젝트 서비스 (project-service)

## 상태
완료

## 날짜
2026-11-10

## 작업 요약
화면이 서버의 프로젝트 API를 부를 때 쓰는 **전화 교환원**을 만들었다. 화면(컴포넌트)은 "프로젝트 목록 주세요"만 말하면 되고, 어느 주소로 어떤 방식으로 요청하는지, 서버가 주는 `snake_case` 응답을 화면용 `camelCase`로 바꾸는 일은 교환원이 맡는다. 인증 토큰 첨부와 401 자동 갱신은 기존 `api-client`가 이미 처리하므로 그대로 재사용했다.

| 함수 | 요청 | 비고 |
|------|------|------|
| `listProjects()` | `GET /projects` | `{projects: [...]}` 에서 배열만 꺼내 변환 |
| `getProject(id)` | `GET /projects/{id}` | 403/404는 `ApiError`로 그대로 던짐 |
| `createProject({title, description?})` | `POST /projects` | 400 검증 오류도 그대로 던짐 |
| `updateProject(id, {title?, description?})` | `PATCH /projects/{id}` | **함수만 제공** (수정 UI는 T059 이후) |
| `deleteProject(id)` | `DELETE /projects/{id}` | **함수만 제공** (삭제 UI는 T060 이후), 204 → `undefined` |

`Project` 타입: `id, title, description(null 가능), createdAt, updatedAt, lastActivityAt, taskCount, completedTaskCount, progressPercent`.

## 변경 파일
- `frontend/src/services/project-service.ts` (신규)
- `frontend/tests/unit/project-service.test.ts` (신규): 10개 케이스 (api-client를 spy로 대체)
- `docs/task-reports/TASK-053-프로젝트-서비스-project-service.md` (신규): 이 보고서

## TDD 결과
- RED 커밋: 해당 없음(Git 저장소 아님). 구현 전 `Failed to resolve import "../../src/services/project-service"`로 테스트 파일이 실패하는 것을 직접 확인했다.
- GREEN 커밋: 해당 없음. 구현 후 10개 통과.
- REFACTOR 커밋: 해당 없음. 기존 `auth-service.ts`와 같은 모양(DTO → 변환 함수 → 얇은 호출 함수)이라 추가 정리할 것이 없었다.
- 테스트 커버리지: `project-service.ts` 문장·분기·함수·줄 100%.

## 기술 결정
- **서비스가 오류를 가공하지 않음**: `api-client`가 이미 모든 오류를 한국어 메시지를 가진 `ApiError`로 바꿔 준다. 서비스에서 한 번 더 잡으면 `status`, `details`(예: `field: "title"`) 정보가 사라질 수 있어 그대로 던진다.
- **`any` 없이 DTO 타입 분리**: 서버 응답 형태(`ProjectDto`)와 화면용 `Project`를 분리해 필드 이름이 바뀌면 컴파일 단계에서 잡힌다.
- **URL 하드코딩 없음**: 경로는 `/projects…`만 쓰고 기준 주소는 `api-client`의 baseURL(`VITE_API_BASE_URL`)을 따른다.

## 비고
- **실제 백엔드와 통합 시 확인할 점**: 이 서비스는 합의된 API 계약(필드명 `last_activity_at`, `completed_task_count`, `progress_percent` 등)을 믿고 작성했다. 백엔드가 완성되면 브라우저(T057~)에서 필드 이름이 정확히 일치하는지 한 번 확인해야 한다.
- Git 저장소가 아니라 커밋은 없다.
