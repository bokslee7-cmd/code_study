# TASK-094. Celery 문서 생성 태스크

## 상태
완료

## 날짜
2026-11-18

## 작업 요약
`backend/src/tasks/document_generation.py`에 `generate_document_task(task_id)`(이름 `documents.generate`, 큐 `document_generation`)를 만들었다. 워커 안에서 `asyncio.run`으로 `DocumentGenerationService.generate_document(task_id)`(T093)를 실행한다.

- **시간 제한(FR-025, 3분):** soft 170초, hard 180초(시도 1회 기준). soft 제한에 걸리면 문서를 `failed`("제한시간(3분)을 넘겨 중단")로 저장하고 예외를 다시 던진다. hard 제한은 워커 자식 프로세스를 죽이는 마지막 안전장치다.
- **재시도 최대 3회(대기 10·20·40초):** 일시적 오류에만 건다. DB 연결 오류(`OperationalError` 등), `ConnectionError`, T093의 자체 재시도를 소진한 뒤에도 남은 재시도 가능 Gemini 오류(`retryable`, 빈 응답)가 해당한다. 재시도 직전에 문서 상태를 `pending`으로 되돌려, 폴링하는 화면이 중간의 `failed`를 보고 멈추지 않게 했다.
- **즉시 실패(재시도 안 함):** 내용 검증 실패(`DocumentGenerationError`), 재시도 불가 Gemini 오류(키 없음·4xx), 태스크 삭제(`NotFoundException`), 그 밖의 버그. 사용자에게 보이는 사유는 고정된 한글 문장이며 내부 예외 문구는 넣지 않는다(상세는 로그).
- 태스크마다 새 이벤트 루프를 쓰므로 DB 엔진도 호출마다 `NullPool`로 새로 만들고 닫는다(풀 연결은 다른 루프에서 재사용할 수 없다).
- `celery_app.py`에 `include=["src.tasks.document_generation"]`을 추가해 워커가 시작할 때 태스크를 등록하게 했다. `src/tasks/__init__.py`(빈 파일)도 추가했다.

## 변경 파일
- `backend/src/tasks/document_generation.py` (신규)
- `backend/src/tasks/__init__.py` (신규, 빈 파일)
- `backend/src/tasks/celery_app.py` (`include` 추가)
- `backend/tests/unit/test_document_generation_task.py` (신규, 16개)
- `specs/001-ai-code-learning-platform/tasks.md` (T094 완료 표시)

## TDD 결과
- RED: 모듈이 없어 테스트가 import 단계에서 실패하는 것을 확인했다.
- GREEN: 16개 통과(등록 설정, 정상 실행, 일시 오류 4종 재시도, 3회 후 실패 기록, 지수 대기, 영구 오류 5종, 한글 사유, soft 제한). 백엔드 전체 955개 통과, ruff·black·mypy(strict) 이상 없음.
- Celery `apply()`(eager)로 재시도 흐름까지 실행했고, DB·Gemini에 닿는 `_generate`/`_record_failure`/`_record_retry`는 async 대역으로 바꿨다.
- **실행하지 않은 것:** 실제 Redis 브로커와 `celery worker` 프로세스로 태스크를 돌려 보지 않았다. 실제 hard/soft 제한 동작과 `include` 등록은 워커를 띄워야 확인된다.

## 기술 결정
- **재시도 대상을 좁혔다.** T093이 이미 Gemini 호출을 최대 3회 재시도하므로, 모든 오류를 다시 시도하면 호출이 최대 4x4번까지 늘 수 있다.
- `_is_transient`가 `DocumentGenerationError.__cause__`를 보고 Gemini 원인을 판별한다(T093이 원인을 `from error`로 이어 두었다).
- 서비스가 이미 저장한 구체적인 실패 사유("유효한 챕터가 3개뿐…")를 워커의 일반 문구가 덮어쓰지 않도록 `mark_failed`는 이미 `failed`인 행을 건드리지 않는다(T095).

## 비고
- 시간 제한은 시도마다 새로 시작하므로, 재시도가 일어나면 사용자가 체감하는 총 시간은 3분을 넘을 수 있다. 총 3분을 엄격히 지키려면 재시도를 없애거나 전체 예산을 따로 계산해야 한다.
- 워커 실행 명령(예: `celery -A src.tasks.celery_app worker -Q document_generation`)은 문서화하거나 docker-compose에 넣지 않았다.
