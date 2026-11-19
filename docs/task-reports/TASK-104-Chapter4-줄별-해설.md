# TASK-104. Chapter4 컴포넌트 (줄별 해설)

## 상태
완료

## 날짜
2026-11-18

## 작업 요약
4장("코드 한 줄씩 완전 해부")을 줄마다 항목(`article`)으로 보여준다. 항목에는 줄 번호 버튼, (파일 경로가 있으면) 파일 경로, 코드, "하는 일", "문법 풀이"를 항상 보여주고 "비유"·"다른 방법"·"주의할 점"은 비어 있지 않을 때만 보여준다.

- `activeLine`과 같은 줄의 항목은 `aria-current="true"`로 강조한다.
- 줄 번호 버튼을 누르면 `onLineSelect({filePath, line})`을 호출한다(코드 쪽 강조·이동에 쓰임).
- `scrollTarget`이 들어오면 그 줄 이하 중 가장 가까운 해설(없으면 그 파일의 첫 해설)로 `scrollIntoView({block: 'nearest'})` 한다. 해설의 `file_path`가 빈 문자열이면 어느 파일과도 맞는 것으로 본다.
- 해설이 없으면 "줄별 해설이 없습니다."

## 변경 파일
- `frontend/src/components/document/chapters/Chapter4.tsx` (신규)
- `frontend/tests/unit/Chapter4.test.tsx` (신규): 10개
- `docs/task-reports/TASK-104-Chapter4-줄별-해설.md` (신규)

## TDD 결과
- RED: Git 저장소가 아니다. 테스트를 먼저 작성했지만 구현 전 단독 실행으로 실패를 확인하지는 않았다.
- GREEN: 첫 실행에서 `scrollIntoView` 호출 대상을 확인하는 테스트 3개가 `mock.contexts`(vitest 1.6에는 없음) 때문에 실패 → `mock.instances`로 고쳐 10개 통과.
- REFACTOR: 없음.

## 기술 결정
- **빈 `file_path`는 와일드카드**: 백엔드가 한 파일짜리 문서에서는 `file_path`를 빈 문자열로 주기 때문에, 코드 패널이 알려 주는 실제 경로(`main.py`)와 맞춰 보려면 필요하다.
- **스크롤은 "이하 중 가장 가까운 줄"**: 코드의 맨 위 줄이 해설이 없는 줄(빈 줄·주석)일 수 있어서다.

## 비고
- 항목 key는 `file_path:line_number`다. 같은 줄 해설이 중복되면 key 경고가 날 수 있다.
- 해설이 많은 문서에서의 스크롤 성능(가상화)은 고려하지 않았다.
