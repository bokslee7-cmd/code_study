# TASK-106. 문서 서비스 (document-service)

## 상태
완료

## 날짜
2026-11-18

## 작업 요약
`frontend/src/services/document-service.ts`에 문서 조회·상태 폴링을 만들었다. 기존 `api-client.ts`·`task-service.ts` 관례(snake_case DTO → camelCase 변환, `apiClient` 사용)와 TanStack Query를 따른다.

- `getDocument(taskId)`: `GET /tasks/{id}/document`. 최상위 필드만 camelCase로 바꾼다(`content`는 AI가 만든 JSON이라 그대로 두고, `file_breakdown` 키는 파일 경로라 변환하면 안 된다). 404이면 `null`("아직 문서가 없음"), 그 밖의 오류는 그대로 던진다.
- `getDocumentStatus(taskId)`: `GET /tasks/{id}/document/status` → `DocumentStatusInfo`(camelCase).
- `useDocument(taskId)`: 문서를 한 번 조회하고, 문서 상태가 `pending`/`in_progress`인 동안에만 상태를 `POLL_INTERVAL_MS`(3000ms)마다 조회한다. 상태가 `completed`/`failed`가 되면 폴링을 멈추고 문서를 다시 조회한다. `{document, status, estimatedRemainingSeconds, isPending, isError, error, refetch}`를 돌려준다.
- 쿼리 키: `['tasks', taskId, 'document']`, `['tasks', taskId, 'document', 'status']`.

## 변경 파일
- `frontend/src/services/document-service.ts` (신규)
- `frontend/tests/unit/document-service.test.tsx` (신규): 13개
- `docs/task-reports/TASK-106-document-service.md` (신규)

## TDD 결과
- RED: Git 저장소가 아니다. 테스트를 먼저 작성했지만 구현 전 단독 실행으로 실패를 확인하지는 않았다.
- GREEN: 13개 통과(가짜 타이머로 3초 간격 폴링·종료 시 중단·문서 재조회를 확인).
- REFACTOR: 없음.

## 기술 결정
- **API 계약 해석**: 문서 행이 없으면 404(한글 메시지) → 오류로 보지 않고 `null`로 처리한다. 폴링은 문서가 이미 있고 생성 중일 때만 한다(문서가 없는 동안에는 폴링하지 않음).
- **상태 쿼리는 문서가 생성 중일 때만 `enabled`**: 완료된 문서를 볼 때 불필요한 상태 요청을 보내지 않는다.

## 비고
- 백엔드(T094~T098)가 없는 상태에서 `apiClient.get`을 모킹해 검증했다. 실제 서버와의 연동은 확인하지 못했다.
- 같은 태스크에서 문서를 다시 생성해 상태가 `completed`에서 다시 `in_progress`가 되는 흐름은 이번에 다루지 않았다(재생성 API가 계약에 없다).
