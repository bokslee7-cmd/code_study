# TASK-080. 태스크 서비스 task-service

## 상태
완료

## 날짜
2026-11-16

## 작업 요약
태스크 API 호출을 한곳에 모은 **서비스 모듈**을 만들었다. 화면은 서버의 snake_case 응답을 몰라도 되도록 이 모듈이 camelCase로 번역해 준다(project-service와 같은 방식). 작업 도중 백엔드 구현(`backend/src/api/tasks.py`, `api/schemas/task.py`)이 생긴 것을 확인해 그 계약에 맞췄다.

| 함수 | 호출 | 비고 |
|------|------|------|
| `listTasks(projectId)` | `GET /projects/{id}/tasks` → `{tasks: [...]}` | |
| `getTask(taskId)` | `GET /tasks/{id}` | |
| `createTask(projectId, input)` | `POST /projects/{id}/tasks` (multipart/form-data) | 아래 필드 참고 |
| `updateTask(taskId, input)` | `PATCH /tasks/{id}` `{title?, description?}` | |
| `deleteTask(taskId)` | `DELETE /tasks/{id}` (204) | |

multipart 필드: `title`, `description`(값이 있을 때만), `upload_method`(`file`|`folder`|`paste`), 파일 업로드는 `files`(반복), 폴더 업로드는 `files`의 **파일 이름 자리에 상대 경로**(`form.append('files', file, file.webkitRelativePath)`), 붙여넣기는 `code`, `language`.

## 변경 파일
- `frontend/src/services/task-service.ts` (신규)
- `frontend/tests/unit/task-service.test.ts` (신규): 11개
- `docs/task-reports/TASK-080-태스크-서비스-task-service.md` (신규)

## TDD 결과
- RED 커밋: 해당 없음(Git 저장소 아님). `task-service.test.ts`를 먼저 작성했지만(fixture `task.ts`가 이 모듈의 타입을 import하는 구조), 서비스 구현 전에 이 파일만 단독으로 RED 실행하지는 않았다. 모듈이 없어 import 실패가 자명한 상태에서 구현을 이어 작성했으며, 이 점을 솔직히 남긴다.
- GREEN 커밋: 해당 없음. 구현 후 11개 통과. 처음에 폴더 경로를 별도 `file_paths` 필드로 보냈다가, 백엔드 `tasks.py`가 "folder: the relative path is the file name"으로 받는 것을 확인하고 `files`의 파일 이름으로 보내도록 구현과 테스트를 고쳤다.
- REFACTOR 커밋: 해당 없음.
- 테스트 커버리지: `task-service.ts` 문장·함수 100%, 분기 88%(`code`/`language`의 `?? ''` 방어 분기 미검증).

## 기술 결정
- **Content-Type을 직접 지정하지 않음**: FormData를 axios에 넘기면 브라우저가 boundary를 포함해 `multipart/form-data`를 정한다. 직접 지정하면 boundary가 빠져 서버가 파싱하지 못한다.
- **`description`은 값이 있을 때만 전송**: 백엔드 `description: str | None = None`과 맞고 빈 문자열을 보내지 않는다.
- **`getTaskCode`(`GET /tasks/{id}/code`)는 만들지 않음**: 이번 범위(T076~T083) 화면 중 쓰는 곳이 없다. 코드 뷰어/문서 생성에서 필요할 때 추가한다.

## 비고
- **가정/확인한 API 계약** (백엔드 `tasks.py`, `schemas/task.py` 기준)
  - `TaskResponse`: `id, project_id, task_number, title, description, upload_method, created_at, updated_at, uploaded_code`. 프런트 `Task`는 `uploaded_code`를 쓰지 않아 무시한다.
  - **`is_completed`는 서버 응답에 없음**: `Task.isCompleted`는 `dto.is_completed ?? false`로 두었다. 서버가 나중에 내려주면 자동 반영되고, 지금은 항상 `false`다.
  - 오류 본문은 기존 `ApiError` 형식(`error`, `message`, `details`, `suggestion`)을 그대로 쓰고, 업로드 오류(`unsupported_extension`, `file_too_large`, `upload_too_large`, `too_many_files`, `binary_file` 등)의 한국어 `message`를 모달이 그대로 보여준다.
  - 백엔드 에이전트가 작업 중이므로 응답 형태가 바뀌면 이 모듈의 `TaskDto`/`toFormData`만 고치면 된다.
- 실제 서버 연동(multipart, 폴더 상대 경로)은 브라우저 수동 테스트(T084~T086)에서 확인이 필요하다.
- Git 저장소가 아니라 커밋은 없다.
