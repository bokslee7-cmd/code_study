# TASK-098. GET /tasks/{task_id}/document/status

## 상태
완료

## 날짜
2026-11-18

## 작업 요약
`backend/src/api/documents.py`에 상태 폴링용 엔드포인트를 추가했다(`/api/v1/tasks/{task_id}/document/status`). 문서 본문·코드를 읽지 않아 가볍다.

```
200 { task_id, status, generation_started_at, generation_completed_at,
      generation_error, failed_chapters, estimated_remaining_seconds }
```
- `estimated_remaining_seconds`: `in_progress`이고 시작 시각이 있을 때만 `max(0, 180 - 경과초)`(정수), 그 외 `null`.
- 인증·소유권·404(문서 행 없음) 처리와 `failed_chapters` 계산은 T097과 같은 함수를 쓴다.
- 응답 스키마 `DocumentStatusResponse`는 `backend/src/api/schemas/document.py`.

## 변경 파일
- `backend/src/api/documents.py`, `backend/src/api/schemas/document.py` (TASK-097과 공용)
- `backend/tests/unit/test_documents_api.py` (TASK-097과 공용)
- `specs/001-ai-code-learning-platform/tasks.md` (T098 완료 표시)

## TDD 결과
- RED: TASK-097과 같은 수집 실패 상태에서 시작했다.
- GREEN: 상태 테스트 7개(완료, 진행 중 추정값, 0 하한, 실패 사유, NULL→pending, 행 없음 404, 남의 태스크 403) 통과. 백엔드 전체 955개 통과.
- 진행 중 추정값은 시작 시각을 현재 기준 30초 전으로 두고 148~150 범위로 검사했다(시계 흐름 허용).

## 기술 결정
- 계약대로 180초 고정 기준으로 계산한다. 실제 소요 시간은 T093 수동 테스트에서 28초였으므로 대부분 과대 추정이다.
- 남의 태스크 403은 TASK-097과 같은 이유다.

## 비고
- `pending`(대기열에 있고 아직 시작 전)에는 `estimated_remaining_seconds`가 `null`이다. 계약이 `in_progress`일 때만 값을 주도록 정했기 때문이다.
