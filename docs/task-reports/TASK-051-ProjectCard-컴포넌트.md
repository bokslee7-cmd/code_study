# TASK-051. ProjectCard 컴포넌트

## 상태
완료

## 날짜
2026-11-10

## 작업 요약
대시보드에 줄지어 놓일 **프로젝트 명함(카드)** 을 만들었다. 도서관 서가에 꽂힌 책 한 권의 책등처럼, 카드 한 장만 봐도 "어떤 프로젝트인지, 얼마나 진행됐는지, 언제 마지막으로 손댔는지"를 알 수 있다.

| 카드에 보이는 것 | 표시 방식 |
|------------------|-----------|
| 제목 | 프로젝트 상세로 가는 링크 (카드 어디를 눌러도 이동) |
| 설명 | 있을 때만 최대 2줄 (없으면 자리 자체를 그리지 않음) |
| 태스크 완료 수 | `2/5 태스크 완료` (태스크가 없으면 `0/0 태스크 완료`) |
| 진행률 | `40%` 글자 + 진행 막대 (`role="progressbar"`, `aria-valuenow`) |
| 마지막 활동일 | `마지막 활동: 2026년 11월 5일` |

진행 상황(완료 수 + 퍼센트 + 막대)은 상세 화면(T055)에서도 똑같이 쓰므로 `ProjectProgress` 컴포넌트로 분리했고, 날짜 표기는 `formatDate` 함수로 분리했다.

카드 전체를 클릭할 수 있게 하되 스크린리더가 읽는 링크 이름은 "제목"만 되도록, 링크를 제목에만 걸고 가상 요소(`after:absolute after:inset-0`)로 클릭 영역을 카드 전체로 넓혔다.

## 변경 파일
- `frontend/src/components/project/ProjectCard.tsx` (신규)
- `frontend/src/components/project/ProjectProgress.tsx` (신규): 완료 수·퍼센트·진행 막대 (카드/상세 공유)
- `frontend/src/lib/format-date.ts` (신규): ISO 문자열 → `2026년 11월 5일`
- `frontend/tests/unit/ProjectCard.test.tsx` (신규): 6개 케이스
- `frontend/tests/fixtures/project.ts` (신규): 테스트용 프로젝트 데이터 공장 `makeProject()`와 서버 응답 샘플
- `docs/task-reports/TASK-051-ProjectCard-컴포넌트.md` (신규): 이 보고서

## TDD 결과
- RED 커밋: 해당 없음(Git 저장소 아님). 구현 전 `Failed to resolve import "../../src/components/project/ProjectCard"`(모듈 없음)로 테스트 파일이 실패하는 것을 직접 확인했다.
- GREEN 커밋: 해당 없음. 구현 후 ProjectCard 6개 통과, 전체 263개 통과.
- REFACTOR 커밋: 해당 없음. 진행 표시를 카드 안에 직접 쓰지 않고 `ProjectProgress`로 뽑아 T055와 공유하게 했다.
- 테스트 커버리지: `ProjectCard.tsx` 100%(문장·분기·함수·줄), `format-date.ts` 100%. `ProjectProgress.tsx`는 카드/상세 테스트를 통해 검증된다.

## 기술 결정
- **링크는 제목에만, 클릭 영역은 카드 전체**: 카드 전체를 `<a>`로 감싸면 링크 이름이 제목+설명+진행률 문구 전체가 되어 스크린리더 사용자에게 장황하다.
- **날짜는 `toLocaleDateString('ko-KR')`**: 별도 날짜 라이브러리를 추가하지 않았다. 사용자의 시간대 기준으로 표시된다(서버 시각이 UTC라면 자정 근처 활동은 날짜가 하루 다르게 보일 수 있다).
- **진행률은 서버 값을 그대로 사용**: 서버가 `progress_percent`를 계산해 주므로 화면에서 다시 계산하지 않는다.

## 비고
- 지금은 Task 모델이 없어 서버가 세 카운트를 항상 0으로 준다. 그래서 화면에는 `0/0 태스크 완료`, `0%`가 자연스럽게 나온다.
- Git 저장소가 아니라 커밋은 없다.
