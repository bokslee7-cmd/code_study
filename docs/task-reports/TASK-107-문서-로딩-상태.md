# TASK-107. 문서 로딩 상태와 진행 표시

## 상태
완료

## 날짜
2026-11-18

## 작업 요약
DocumentViewer의 대기·진행·실패 화면을 만들었다.

- 문서 조회 중: `role="status"` "문서를 불러오는 중입니다..."
- `pending`: "문서 생성을 기다리는 중입니다", `in_progress`: "문서를 만드는 중입니다" + `role="progressbar"`(이름 "문서 생성 진행 상황", 값 없는 진행 중 표시) + 예상 남은 시간. 코드·설명 영역은 그리지 않는다.
- 예상 남은 시간(`lib/format-remaining-time.ts`): `40` → "예상 남은 시간: 약 40초", `90` → "약 1분 30초", `0` → "곧 완료됩니다", `null` → "예상 시간을 계산하는 중입니다". 폴링 값이 바뀌면 같이 바뀐다.
- `failed`: 빨간 오류 배너(`role="alert"`, `bg-red-50`)에 "문서를 만들지 못했습니다.", "사유: {generation_error}"(없으면 "알 수 없는 오류"), "잠시 후 다시 시도해 주세요. 문제가 계속되면 코드를 다시 올려 새 태스크로 만들어 보세요." 안내와 "다시 확인" 버튼(문서를 다시 조회).

## 변경 파일
- `frontend/src/components/document/GenerationProgress.tsx` (신규)
- `frontend/src/lib/format-remaining-time.ts` (신규)
- `frontend/src/components/document/DocumentViewer.tsx` (T105와 같은 파일, 상태 분기)
- `frontend/tests/unit/DocumentViewerLoading.test.tsx` (신규): 14개
- `docs/task-reports/TASK-107-문서-로딩-상태.md` (신규)

## TDD 결과
- RED: Git 저장소가 아니다. 구현 전 `DocumentViewer`·`format-remaining-time`을 해석하지 못해 실패하는 것을 확인했다(T105와 함께 실행).
- GREEN: 14개 통과. 폴링으로 `in_progress`에서 `completed`로 바뀌면 진행 표시가 사라지고 문서가 나타나는 흐름도 가짜 타이머로 확인했다.
- REFACTOR: 없음.

## 기술 결정
- **재시도 안내를 문구 + "다시 확인"으로 한 이유**: 백엔드 계약에 재생성 API가 없어 "다시 만들기" 버튼은 만들지 않았다. 버튼은 문서 상태를 다시 읽기만 한다. 재생성이 필요하면 문구대로 새 태스크로 올리게 안내한다.
- **진행 막대는 값 없음**: 서버가 비율을 주지 않아 가짜 퍼센트를 만들지 않고 "진행 중" 표시와 남은 시간만 보여 준다.

## 비고
- "코드를 다시 올려 새 태스크로" 안내 문구는 계약에 재생성이 없다는 가정에서 쓴 것이다. 재생성 API가 생기면 이 문구와 버튼을 바꿔야 한다.
- 부분 성공 배너는 TASK-105에서 다뤘다.
