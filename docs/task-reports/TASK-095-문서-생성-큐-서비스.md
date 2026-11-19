# TASK-095. 문서 생성 큐 서비스 (상태 추적)

## 상태
완료

## 날짜
2026-11-18

## 작업 요약
`backend/src/services/document/document_queue_service.py`에 `DocumentQueueService`를 구현했다. 별도 큐 테이블 없이 `LearningDocument` 행이 큐 항목 역할을 한다. `pending`+`celery_task_id` = 대기 중, `in_progress` = 생성 중(T093이 설정), `completed`/`failed` = 종료.

- `enqueue(task_id)`: 행을 `FOR UPDATE`로 잠그고(없으면 빈 챕터 7개 뼈대의 `pending` 행 생성), 이미 대기·생성 중이면 아무것도 하지 않고 기존 행을 돌려준다. 그 외(새 행, celery id 없는 `pending`, 종료된 행)는 상태를 초기화하고 새 celery id를 저장한 뒤 **commit하고 나서** Celery에 보낸다.
- `regenerate(task_id)`: 같은 흐름이지만 대기·생성 중이면 409(`conflict`, 한글 메시지).
- `get_document(task_id)`: 상태 조회(행 또는 None). 순수 함수 `failed_chapters(content)`, `estimate_remaining_seconds(document)`(`in_progress`일 때만 `180 - 경과`, 0 미만이면 0)를 같은 모듈에 두었다.
- `mark_failed`/`mark_pending`: 워커(T094)가 서비스가 기록하지 못한 실패·재시도를 반영할 때 쓴다.
- 큐 전송 실패(Redis 꺼짐 등)는 예외로 올리지 않고 행을 `failed`("대기열에 등록하지 못했습니다")로 저장한다.
- 기본 전송 함수는 `src.tasks.document_generation`을 호출 시점에 import한다(`celery_app`이 import 때 `REDIS_URL`을 요구하므로, API 서버는 Redis 설정 없이도 떠야 한다). 전송은 `asyncio.to_thread`로 이벤트 루프 밖에서 하고, 브로커 연결 재시도는 1회로 제한했다.

## 변경 파일
- `backend/src/services/document/document_queue_service.py` (신규)
- `backend/src/api/dependencies.py` (`get_document_queue_service` 추가)
- `backend/tests/unit/test_document_queue_service.py` (신규, 26개)
- `backend/tests/integration/test_document_queue_integration.py` (신규, 6개, 실제 PostgreSQL 필요)
- `specs/001-ai-code-learning-platform/tasks.md` (T095 완료 표시)

## TDD 결과
- RED: 모듈이 없어 수집 단계에서 실패하는 것을 확인했다.
- GREEN: 단위 26개 + 통합 6개 통과. 통합 테스트는 임시 DB에 마이그레이션을 적용하고 실제 앱·`get_session`으로 업로드 → 대기 행 → 엔드포인트 응답을 확인한다(Celery 전송 함수만 대역). 백엔드 전체 955개 통과.
- **실행하지 않은 것:** 실제 Redis/Celery로 `apply_async`를 호출해 보지 않았다(기본 전송 함수는 가짜 모듈로 인자만 검증).

## 기술 결정
- **commit 후 전송:** 요청 세션은 응답 뒤에 commit되는데, 그 전에 보내면 워커가 아직 보이지 않는 태스크를 찾다 404로 실패한다. T093처럼 이 서비스도 직접 commit한다(프로젝트 관례의 예외).
- **celery id를 전송 전에 저장:** 워커가 즉시 시작해도 행에 id가 있고, `apply_async(task_id=...)`로 같은 id를 쓴다.
- **멈춘 `in_progress` 처리:** 시작 후 300초(hard 제한 180초 + 여유 120초)가 지나면 죽은 실행으로 보고 다시 시작할 수 있게 했다. 없으면 워커가 죽었을 때 영원히 "생성 중"에 갇힌다.
- 같은 태스크의 첫 행을 동시에 만들면 `task_id` UNIQUE로 한쪽이 `IntegrityError`가 난다. 업로드는 태스크당 한 번이라 별도 처리하지 않았다.

## 비고
- 대기(`pending`+celery id)가 오래 지속되는 경우(브로커가 메시지를 잃음)는 감지하지 않는다. `pending`에는 시작 시각이 없어서다.
- 재생성을 호출하는 HTTP 엔드포인트는 요청 범위(T097·T098)에 없어 만들지 않았다. 서비스 메서드만 있다.
