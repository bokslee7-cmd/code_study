# TASK-079. TaskCard 컴포넌트

## 상태
완료

## 날짜
2026-11-16

## 작업 요약
프로젝트 타임라인에 쌓이는 **태스크 카드**를 만들었다. 책의 목차 한 줄처럼 `Task 1`(번호), 제목, 설명, 생성일을 보여주고 누르면 해당 태스크로 이동한다.

| 항목 | 동작 |
|------|------|
| 번호 | `Task {taskNumber}` |
| 제목 | `/projects/{projectId}/tasks/{id}`로 가는 링크, ProjectCard와 같이 카드 전체가 클릭 영역(after 가상 요소) |
| 설명 | 있으면 2줄까지(`line-clamp-2`), 없으면 그리지 않음 |
| 생성일 | `생성일: 2026년 11월 2일` |
| 완료 표시 | `isCompleted`일 때만 `완료` |

## 변경 파일
- `frontend/src/components/task/TaskCard.tsx` (신규)
- `frontend/tests/unit/TaskCard.test.tsx` (신규): 5개
- `frontend/tests/fixtures/task.ts` (신규): `makeTask`, `serverTask`
- `docs/task-reports/TASK-079-TaskCard-컴포넌트.md` (신규)

## TDD 결과
- RED 커밋: 해당 없음(Git 저장소 아님). 구현 전 `Failed to resolve import "../../src/components/task/TaskCard"`로 실패하는 것을 확인했다.
- GREEN 커밋: 해당 없음. 구현 후 5개 통과.
- REFACTOR 커밋: 해당 없음.
- 테스트 커버리지: `TaskCard.tsx` 100%.

## 기술 결정
- **카드 구조는 ProjectCard를 따름**: 링크 이름이 제목만 되도록 제목에만 링크를 걸고 카드 전체 클릭은 CSS로 확장해 스크린리더 읽기를 단순하게 유지한다.
- **`Task` 타입은 task-service.ts(TASK-080)에서 가져옴**: 카드·페이지·서비스가 같은 타입을 쓴다.

## 비고
- `isCompleted`는 백엔드 `TaskResponse`에 아직 없는 필드다(TASK-080 비고 참고). 없으면 `false`로 처리되어 `완료` 표시는 나오지 않는다. 서버가 나중에 내려주면 그대로 표시된다.
- Git 저장소가 아니라 커밋은 없다.
