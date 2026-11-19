# TASK-097. GET /tasks/{task_id}/document

## 상태
완료

## 날짜
2026-11-18

## 작업 요약
`backend/src/api/documents.py`에 학습 문서 조회 엔드포인트를 만들고 `router.py`에 등록했다(최종 경로 `/api/v1/tasks/{task_id}/document`). 응답 스키마는 `backend/src/api/schemas/document.py`(`DocumentResponse`, `DocumentFile`)에 두었다.

```
200 { id, task_id, status: pending|in_progress|completed|failed,
      content: {chapter1..chapter7}, failed_chapters: ["chapter4"],
      generation_error, generation_started_at, generation_completed_at,
      files: [{path, language, content}] }
```
- 순서: 로그인(401) → `tasks.get_owned`(없거나 휴지통이면 404, 남의 것이면 403) → 문서 행 없으면 404("이 태스크의 학습 문서를 찾을 수 없습니다…" + 제안) → 코드 읽기.
- `failed_chapters`는 `content[chN] == {"generation_failed": true}`인 챕터(챕터 순서).
- `files[].path`는 `file_path`, 없으면 `file_name`. 서버 저장 경로·DB id는 노출하지 않는다.
- 상태 컬럼이 NULL(마이그레이션상 허용)이면 `pending`으로 응답한다.

## 변경 파일
- `backend/src/api/documents.py` (신규)
- `backend/src/api/schemas/document.py` (신규)
- `backend/src/api/router.py` (documents 라우터 등록)
- `backend/src/api/dependencies.py` (TASK-095에서 추가한 `get_document_queue_service` 사용)
- `backend/tests/unit/test_documents_api.py` (신규, 19개: T097·T098 공용)
- `specs/001-ai-code-learning-platform/tasks.md` (T097 완료 표시)

## TDD 결과
- RED: `get_document_queue_service`가 없어 수집 단계에서 실패하는 것을 확인했다.
- GREEN: 19개 통과(T098 포함). 백엔드 전체 955개 통과, ruff·black·mypy(strict) 이상 없음. 실제 PostgreSQL을 쓰는 통합 테스트(TASK-095 파일)로 업로드 직후 `pending` 문서·파일 목록 응답, 남의 태스크 403, 없는 태스크 404도 확인했다.
- **실행하지 않은 것:** 실제 Gemini로 생성된 문서를 이 API로 조회해 보지 않았다(T093 수동 테스트에서 저장된 content 형태만 확인).

## 기술 결정
- **계약과 다른 점: 남의 태스크는 404가 아니라 403.** 기존 `/tasks/{id}`, `/tasks/{id}/code`가 `TaskService.get_owned`를 통해 403을 돌려주므로 그 관례를 그대로 따랐다. 404로 바꾸려면 `get_owned`를 바꿔야 하고 기존 엔드포인트 전체에 영향이 간다(범위 밖).
- `content`는 저장된 JSON을 가공 없이 그대로 돌려준다.

## 비고
- 문서 행이 없는 태스크(예: 이 기능 도입 전에 만든 태스크)는 404이고, 재생성 엔드포인트가 없어 지금은 화면에서 복구할 방법이 없다.
