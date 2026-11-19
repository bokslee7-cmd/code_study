# TASK-096. 코드 업로드 후 문서 생성 트리거

## 상태
완료

## 날짜
2026-11-18

## 작업 요약
`TaskService.start_document_generation(task)`를 추가하고, 태스크 생성 API(`POST /projects/{id}/tasks`)가 코드 저장(`uploads.store`) 성공 직후 호출하게 했다. 내부에서 `DocumentQueueService.enqueue(task.id)`를 부른다. `TaskService`에는 업로드 메서드가 없고 저장은 `CodeUploadService.store`가 맡으므로, 라우터에서 저장 다음 줄에 호출하는 형태다.

- 큐잉이 어떤 이유로 실패해도 예외를 삼키고 로그(`logger.exception`)만 남긴다. 코드는 이미 저장됐으므로 업로드(201)는 성공한다.
- `TaskService(session, document_queue=None)`: 두 번째 인자는 선택이라 기존 호출은 그대로 동작한다.
- 업로드 검증이 실패하면(400) 태스크도 문서도 만들어지지 않는다(트리거 미호출을 테스트로 확인).

## 변경 파일
- `backend/src/services/task_service.py` (`start_document_generation`, 생성자 선택 인자)
- `backend/src/api/tasks.py` (`store` 다음에 호출)
- `backend/tests/unit/test_task_service.py` (3개 추가)
- `backend/tests/unit/test_tasks_api.py` (하니스에 `start_document_generation` 대역 추가, 2개 추가)
- `specs/001-ai-code-learning-platform/tasks.md` (T096 완료 표시)

## TDD 결과
- RED: 새 테스트 4개 실패(`start_document_generation`/`document_queue` 없음). 기존 테스트 76개는 통과 상태였다.
- GREEN: 80개 통과. 기존 `test_tasks_api.py`의 하니스는 `MagicMock(spec=TaskService)`라 새 메서드가 `await` 불가능한 대역이 되므로 `AsyncMock` 한 줄을 추가했다(기존 테스트 본문은 수정하지 않음). 백엔드 전체 955개 통과.
- 통합 테스트(TASK-095의 파일)에서 실제 앱·DB로 업로드 → `pending` 행 + 전송 1회, 큐 장애 시에도 201임을 확인했다.

## 기술 결정
- **큐잉 실패 시 문서 상태는 `failed`(+사유), 업로드는 성공.** `pending`으로 두면 화면이 영원히 "생성 중"을 보여 주고 복구 수단이 없다. `failed`로 두면 상태 폴링이 곧바로 끝나고 사용자가 재생성할 수 있다. 사유 문구는 "문서 생성 작업을 대기열에 등록하지 못했습니다. 잠시 후 다시 시도하세요."이며, 이 판단은 큐 서비스(T095)가 한다. `TaskService`는 그 밖의 예상 못 한 예외만 로그로 남긴다.
- 이 호출은 요청 세션을 중간에 commit한다(T095 결정). 업로드가 성공한 시점이라 되돌릴 일이 없다.

## 비고
- 큐 서비스 안에서 DB 오류가 나면 요청 세션이 깨져 응답 뒤 commit이 실패할 수 있다. 가능성이 낮아 별도 처리하지 않았다.
- Celery/Redis를 실제로 끈 상태의 HTTP 업로드는 실행해 보지 않았다. 전송 함수가 예외를 던지는 상황을 대역으로 재현해 확인했다.
