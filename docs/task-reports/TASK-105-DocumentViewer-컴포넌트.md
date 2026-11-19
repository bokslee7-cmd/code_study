# TASK-105. DocumentViewer 컴포넌트 (2열 + 동기 스크롤)

## 상태
완료

## 날짜
2026-11-18

## 작업 요약
`DocumentViewer({taskId})`가 `useDocument`(T106)로 문서를 불러와 상태별로 화면을 고른다. 완료된 문서는 넓은 화면(`lg`)에서 코드(`region "코드"`) | 설명(`region "설명"`) 2열 그리드로 보여준다.

- 코드 → 설명: 코드를 스크롤하면 `CodePanel`이 알려 준 맨 위 줄로 `ExplanationPanel`(4장을 보는 중일 때)이 가장 가까운 줄 해설로 스크롤하고 그 항목을 현재 항목으로 표시한다.
- 설명 → 코드: 4장의 줄 번호 버튼을 누르면 코드에서 그 줄을 강조하고 가운데로 스크롤한다(다른 파일이면 탭 전환).
- 줄을 가리킨 쪽(`source: 'code' | 'explanation'`)만 상태에 기록해, 상대 패널만 반응하고 서로 되돌려 보내지 않는다(코드 스크롤로 정해진 줄은 코드 강조로 넘기지 않음).
- 부분 성공(`failedChapters` 비어 있지 않음): 노란 경고 배너(`role="status"`, `bg-yellow-50`) "일부 섹션을 만들지 못했습니다. 질문하기로 보충할 수 있어요." 아래에 문서를 보여준다. 실패 챕터는 T101의 "생성 실패" 안내로 대체된다.
- 문서 전체가 `failed`: 빨간 오류 배너(T107).
- 조회 오류: 서버 메시지(`ApiError`) 또는 일반 안내와 "다시 시도" 버튼. 문서가 아직 없으면(404 → null) "아직 문서가 없습니다."

## 변경 파일
- `frontend/src/components/document/DocumentViewer.tsx` (신규)
- `frontend/tests/unit/DocumentViewer.test.tsx` (신규): 14개. `CodeEditor`를 모킹하고 `apiClient.get`을 주소별로 흉내 낸다.
- `frontend/tests/fixtures/document.ts` (신규): 문서·챕터·상태 픽스처와 `mockDocumentApi`
- `docs/task-reports/TASK-105-DocumentViewer-컴포넌트.md` (신규)

## TDD 결과
- RED: Git 저장소가 아니다. 구현 전 실행에서 `DocumentViewer`를 해석하지 못해 2개 테스트 파일이 실패하는 것을 확인했다.
- GREEN: 첫 실행에서 14개 중 1개 실패(테스트가 로딩 `status`를 먼저 집던 문제 → 테스트에서 설명 영역이 뜰 때까지 기다리도록 수정), `tsc` 오류(`document`가 `undefined`일 수 있음 → `!document`로 좁힘) 수정 후 통과.
- REFACTOR: 없음.

## 기술 결정
- **동기화에 `source`를 둔 이유**: 코드 스크롤 → 설명 스크롤 → (강조로) 코드 스크롤 되돌림 같은 되먹임을 끊기 위해서다. 편집기 쪽에서도 강조로 인한 프로그램 스크롤은 300ms 동안 알림에서 제외한다(T099).
- **동기 스크롤은 4장에만 적용**: 줄 단위 해설은 4장에만 있다. 다른 챕터를 보는 중에는 코드 스크롤이 설명에 영향을 주지 않는다.

## 비고
- 실제 Monaco에서의 스크롤 동기화는 자동 테스트로 확인하지 못했다(모킹한 편집기로 콜백 연결만 검증). 브라우저 확인은 T109~T114 범위다.
- 좁은 화면(`lg` 미만)에서는 코드 위, 설명 아래로 세로로 쌓이며 이때도 동기화는 동작하지만 두 패널이 동시에 보이지 않을 수 있다.
