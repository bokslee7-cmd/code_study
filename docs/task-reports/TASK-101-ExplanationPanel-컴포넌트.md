# TASK-101. ExplanationPanel 컴포넌트

## 상태
완료

## 날짜
2026-11-18

## 작업 요약
문서의 설명 쪽 패널을 만들었다. 위쪽에 7개 챕터 버튼(번호 + 제목)을 두고, 선택한 챕터 하나를 아래에 보여준다. 처음에는 1장이고, 현재 챕터 버튼은 `aria-current="step"`으로 강조한다. 챕터 선택 상태는 이 컴포넌트가 가진다.

- 1·2·4장은 전용 컴포넌트(T102~T104), 3·5·6·7장은 `chapters/GenericChapter.tsx`의 최소 범용 렌더링(제목 + 핵심 필드)을 쓴다.
  - 3장: 플로우차트(`pre`) + 파일별 역할
  - 5장: 단계별 일어나는 일 / 변수 값 / 설명
  - 6장: 개념별 무엇인가요 / 왜 쓰나요 / 어디에 쓰였나요
  - 7장: 실수 제목 / 틀린 코드 / 올바른 코드 / 왜 문제인가요 / 고치는 방법
- 실패 챕터(`failedChapters`에 있거나 값이 `{generation_failed: true}`)는 본문 대신 "생성 실패"와 "이 섹션을 만들지 못했습니다. 질문하기로 보충할 수 있어요." 안내를 보여주고, 버튼에는 기본 제목과 "(생성 실패)"를 붙인다.
- 내용이 아직 없는 챕터는 "이 챕터의 내용이 아직 없습니다."
- 4장에 `activeLine`·`scrollTarget`·`onLineSelect`를 그대로 전달한다.

## 변경 파일
- `frontend/src/components/document/ExplanationPanel.tsx` (신규)
- `frontend/src/components/document/chapters/GenericChapter.tsx` (신규)
- `frontend/tests/unit/ExplanationPanel.test.tsx` (신규): 14개
- `docs/task-reports/TASK-101-ExplanationPanel-컴포넌트.md` (신규)

## TDD 결과
- RED: Git 저장소가 아니다. 테스트를 먼저 작성했지만 구현 전 단독 실행으로 실패를 확인하지는 않았다.
- GREEN: T100~T104 구현 후 처음 실행에서 통과(14개).
- REFACTOR: 없음.

## 기술 결정
- **챕터 선택은 비제어(내부 상태)**: 챕터 선택을 DocumentViewer가 알 필요가 없어서 props를 늘리지 않았다.
- **범용 렌더링은 한 파일에 모음**: 챕터 3·5·6·7은 전용 컴포넌트가 이번 범위가 아니라 `GenericChapter` 하나에서 챕터 키로 분기한다.

## 비고
- 챕터 3의 플로우차트는 서버가 준 ASCII 문자열을 `pre`로만 보여준다.
- 읽은 챕터 진행률 추적(US5)은 이번 범위가 아니다.
