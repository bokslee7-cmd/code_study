# TASK-100. CodePanel 컴포넌트

## 상태
완료

## 날짜
2026-11-18

## 작업 요약
문서의 코드 쪽 패널을 만들었다. 파일이 하나면 경로만, 여러 개면 파일 탭을 보여주고 선택한 파일의 코드를 `CodeEditor`(T099)로 읽기 전용 표시한다.

- `highlight`(`{filePath, line}`)가 현재 파일의 줄이면 그 줄 번호를 편집기에 넘긴다. `filePath`가 빈 문자열이면 현재(유일한) 파일의 줄로 본다.
- `highlight`가 다른 파일을 가리키면 그 파일 탭으로 옮겨 간다(처음 렌더에서도 적용).
- 스크롤하면 `onVisibleLineChange({filePath, line})`으로 현재 파일과 맨 위 줄을 알린다.
- 파일이 없으면 "표시할 코드가 없습니다."

## 변경 파일
- `frontend/src/components/document/CodePanel.tsx` (신규)
- `frontend/tests/unit/CodePanel.test.tsx` (신규): 9개. `CodeEditor`를 모킹한다.
- `docs/task-reports/TASK-100-CodePanel-컴포넌트.md` (신규)

## TDD 결과
- RED: Git 저장소가 아니다. 테스트를 먼저 작성했지만 구현 전 단독 실행으로 실패를 확인하지는 않았다(다른 컴포넌트 테스트와 함께 구현 직후 처음 실행).
- GREEN: 첫 실행에서 1개 실패(처음 렌더에서 다른 파일을 가리키는 highlight를 무시) → 초기 선택 경로를 highlight 기준으로 계산하도록 고쳐 9개 통과.
- REFACTOR: 없음.

## 기술 결정
- **highlight 변경 시 탭 전환은 렌더 중 상태 보정**: effect에서 setState 하지 않는 React 권장 방식(이전 highlight를 상태로 보관해 비교)을 썼다.
- **"파일 하나면 탭 없음"**: 탭이 하나뿐이면 선택지가 아니라 잡음이어서 경로 문구로 대체했다.

## 비고
- 구문 강조는 Monaco 자체 기능이다. 서버가 주는 `language` 값이 Monaco가 모르는 이름이면 강조 없이 표시된다.
