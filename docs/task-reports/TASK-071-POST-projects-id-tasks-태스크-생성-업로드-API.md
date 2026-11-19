# TASK-071. POST projects id tasks 태스크 생성 업로드 API

## 상태
완료

## 날짜
2026-11-16

## 작업 요약
`POST /api/v1/projects/{project_id}/tasks` (multipart/form-data) -> 201 `TaskResponse`.

| 폼 필드 | 필수 | 설명 |
|---------|------|------|
| `title` | O | 5~255자 |
| `upload_method` | O | `file`, `folder`, `paste` |
| `description` | X | 최대 500자 |
| `files` | file/folder | 여러 개 가능. folder는 파일의 filename을 상대 경로로 보냄(`webkitRelativePath`) |
| `code`, `language` | paste | 붙여넣은 코드와 언어 드롭다운 값 |

순서: 업로드 검증(`prepare_*`) -> 태스크 생성(번호 부여) -> 파일 저장/분석(`store`). 검증 실패 시 태스크가 만들어지지 않는다. 각 파일은 한도+1바이트까지만 읽는다.

오류: 400(폼 누락/잘못된 방식/검증 코드: `no_files`, `unsupported_extension`, `binary_file`, `too_many_files`, `invalid_path`, `unsupported_language`, `empty_code`), 413(`file_too_large`, `upload_too_large`), 401, 403, 404.

## 변경 파일
- `backend/src/api/tasks.py`, `backend/tests/unit/test_tasks_api.py` (T070과 공용)
- `specs/001-ai-code-learning-platform/tasks.md` (T071 완료 표시)

## TDD 결과
- RED: 구현 전 테스트를 먼저 작성하고 실행해 수집 단계 오류(모듈/라우트 부재)로 실패함을 확인함
- GREEN: 최소 구현 후 통과 확인
- REFACTOR: black / ruff / mypy 통과 확인
- 전체 백엔드: 736 passed, 47 skipped (이전 608 passed, 43 skipped). skipped는 PostgreSQL이 필요한 통합 테스트로, 이 환경에 DB가 없어 실행되지 않음
- 커밋: Git 저장소가 아니라 없음
- 이 엔드포인트 테스트: 3가지 방식, 폼 누락, 알 수 없는 방식, 업로드/태스크 검증 오류 전달, 403, 파일당 읽기 상한

## 기술 결정
- FastAPI 0.104에서 `list[UploadFile] | None`은 인식되지 않아 `Annotated[list[UploadFile], File()] = []`를 썼다(`B006` noqa, 변경하지 않는 값).
- 오류의 `error` 필드에 검증 코드를 그대로 쓴다(`ErrorResponse.error`).

## 비고
- 라우트는 `backend/src/api/router.py`에 `tasks.router` 한 줄만 추가해 등록했다. 서비스 의존성(`get_task_service`, `get_code_upload_service`)은 `dependencies.py`에 추가했다.
- 한계: 요청 본문 전체 크기를 읽기 전에 제한하는 미들웨어는 없다. 파일당 10MB+1까지만 메모리에 올리고 합계 검증으로 거부하므로 최악 메모리는 `파일 수(최대 폼 파트 수) x 10MB`다. 필요하면 후속으로 Content-Length 제한을 추가한다.
- 문서 생성 트리거(요구 사항 addendum의 시간당 3회 제한 등)는 이 태스크 범위가 아니다.
