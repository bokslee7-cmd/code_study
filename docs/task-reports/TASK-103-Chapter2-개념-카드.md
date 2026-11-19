# TASK-103. Chapter2 컴포넌트 (개념 카드)

## 상태
완료

## 날짜
2026-11-18

## 작업 요약
2장("알아야 할 기본 개념")을 개념 카드로 보여준다. 개념마다 `article` 카드를 만들고, 개념 이름을 `h4`로, 설명·비유·예시·사용처를 라벨(`dt`)과 값(`dd`)으로 보여준다. 예시는 코드 모양(`code`)으로 표시한다. 개념이 없으면 "설명할 개념이 없습니다."

## 변경 파일
- `frontend/src/components/document/chapters/Chapter2.tsx` (신규)
- `frontend/tests/unit/Chapter2.test.tsx` (신규): 4개
- `docs/task-reports/TASK-103-Chapter2-개념-카드.md` (신규)

## TDD 결과
- RED: Git 저장소가 아니다. 테스트를 먼저 작성했지만 구현 전 단독 실행으로 실패를 확인하지는 않았다.
- GREEN: 4개 통과.
- REFACTOR: 없음.

## 기술 결정
- 카드 안 필드 순서(설명·비유·예시·사용처)는 CHAPTER_SCHEMA의 `chapter2.concepts` 필드 순서를 따랐다.

## 비고
- 카드의 key는 개념 이름이다. 같은 이름의 개념이 두 번 오면 React key 경고가 날 수 있다(프롬프트상 최대 5개이고 이름이 겹칠 가능성은 낮다고 보았다).
