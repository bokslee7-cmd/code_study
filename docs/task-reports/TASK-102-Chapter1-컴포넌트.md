# TASK-102. Chapter1 컴포넌트

## 상태
완료

## 날짜
2026-11-18

## 작업 요약
1장("이 코드가 하는 일")을 보여주는 컴포넌트. 챕터 제목을 `h3`로, `summary`(쉬운 말 한 문장)를 본문으로 보여준다.

## 변경 파일
- `frontend/src/components/document/chapters/Chapter1.tsx` (신규)
- `frontend/tests/unit/Chapter1.test.tsx` (신규): 1개
- `docs/task-reports/TASK-102-Chapter1-컴포넌트.md` (신규)

## TDD 결과
- RED: Git 저장소가 아니다. 테스트를 먼저 작성했지만 구현 전 단독 실행으로 실패를 확인하지는 않았다.
- GREEN: 1개 통과.
- REFACTOR: 없음.

## 기술 결정
- 요구된 필드(title, summary)만 그렸다. 아이콘·강조 같은 꾸밈은 넣지 않았다.

## 비고
- 없음.
