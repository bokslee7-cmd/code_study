# TASK-108. TaskDetail 문서 탭 연결

## 상태
완료

## 날짜
2026-11-18

## 작업 요약
`TaskDetail` 페이지의 "문서" 탭 내용을 "학습 문서는 준비 중입니다." 자리표시자에서 `DocumentViewer`로 바꿨다. 주소의 `taskId`로 문서를 조회하고, 상태에 따라 진행 표시·문서·오류를 보여준다. 연습문제·Q&A 탭은 그대로 "준비 중입니다." 안내다.

- 2열 문서 화면이 들어가도록 페이지 폭을 `max-w-3xl`에서 `max-w-6xl`로 넓혔다.

## 변경 파일
- `frontend/src/pages/TaskDetail.tsx`
- `frontend/tests/unit/TaskDetail.test.tsx`: 문서 탭 자리표시자 기대를 문서 없음 안내로 바꾸고 2개 추가(총 13개). 문서 API(`apiClient.get`)와 `CodeEditor`를 모킹하는 `beforeEach` 추가.
- `docs/task-reports/TASK-108-TaskDetail-문서-탭.md` (신규)

## TDD 결과
- RED: Git 저장소가 아니다. 테스트를 먼저 고친 뒤 실행해 3개 실패(자리표시자 문구가 남아 있음, 문서 미표시, 진행 상태 미표시)를 확인했다.
- GREEN: `TaskDetail.test.tsx` 13개 통과(처음에는 새 테스트가 탭 패널이 뜨기 전에 동기적으로 조회해 1개 실패 → 테스트에서 `findByRole`로 기다리도록 수정).
- REFACTOR: 없음.

## 기술 결정
- **기존 테스트 수정**: 문서 탭 자리표시자가 사라지는 것이 이 Task의 요구라서 그 문구를 확인하던 기존 단언을 바꿨다. 다른 단언(태스크 정보, 탭 이름, 오류 상태)은 그대로다.
- **탭 전환 시 상태**: Radix Tabs가 비활성 탭 내용을 언마운트하므로 연습문제 탭에 갔다 오면 DocumentViewer 상태(챕터 선택 등)는 초기화되고, 서버 데이터는 쿼리 캐시로 다시 쓴다.

## 비고
- 브라우저에서의 실제 화면 확인(T109~T114)은 이번 범위가 아니다.
