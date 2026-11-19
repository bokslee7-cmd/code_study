# TASK-083. TaskDetail 페이지 골격

## 상태
완료

## 날짜
2026-11-16

## 작업 요약
태스크 카드를 눌렀을 때 도착하는 **태스크 상세 페이지의 뼈대**를 만들었다. 건물로 치면 방(문서·연습문제·Q&A)의 문패와 빈 방만 달아 둔 상태이며, 방 안의 내용은 Phase 6~8에서 채운다.

| 영역 | 내용 |
|------|------|
| 상단 | `프로젝트로 돌아가기`(`/projects/{projectId}`) 링크, 로딩·오류 상태에서도 항상 표시 |
| 정보 | `Task {번호}`, 제목(h1), 설명(있을 때만), `생성일: ...` |
| 탭 | `문서`(기본) / `연습문제` / `Q&A` (Radix Tabs). 각 패널은 `학습 문서는 준비 중입니다.` / `연습문제는 준비 중입니다.` / `Q&A는 준비 중입니다.` |

| 상태 | 화면 |
|------|------|
| 로딩 | `태스크를 불러오는 중입니다...` |
| 403 | `이 태스크에 접근할 권한이 없습니다.` (재시도 없음) |
| 404 | `태스크를 찾을 수 없습니다. 삭제되었거나 주소가 잘못되었을 수 있습니다.` (재시도 없음) |
| 그 밖의 오류 | 서버 메시지 + `다시 시도` / 서버 메시지가 없으면 `태스크를 불러오지 못했습니다. 잠시 후 다시 시도하세요.` |

쿼리 키는 `["projects", projectId, "tasks", taskId]`다. **라우팅**: `App.tsx`의 `/projects/:projectId/tasks/:taskId` 라우트 element를 `PagePlaceholder`에서 `<TaskDetail />`로 교체했다(필요 최소 변경).

## 변경 파일
- `frontend/src/pages/TaskDetail.tsx` (신규)
- `frontend/src/App.tsx`: TaskDetail import와 라우트 element 교체
- `frontend/tests/unit/TaskDetail.test.tsx` (신규): 11개
- `frontend/tests/unit/App.test.tsx`: 태스크 상세 라우트가 태스크 제목을 그리는지 확인하도록 갱신(TASK-082와 같은 파일 변경)
- `docs/task-reports/TASK-083-TaskDetail-페이지-골격.md` (신규)

## TDD 결과
- RED 커밋: 해당 없음(Git 저장소 아님). 구현 전 `Failed to resolve import "../../src/pages/TaskDetail"`로 TaskDetail 테스트가 실패하고, `App.test.tsx`의 태스크 상세 라우트 케이스도 실패하는 것을 확인했다.
- GREEN 커밋: 해당 없음. 구현 후 TaskDetail 11개, App 11개 통과, 전체 360개 통과.
- REFACTOR 커밋: 해당 없음.
- 테스트 커버리지: `TaskDetail.tsx` 문장·분기·함수 100%.

## 기술 결정
- **ProjectDetail과 같은 오류 처리 패턴**: 403/404는 화면 고정 문구에 재시도 없음. 두 페이지의 `errorMessage`/`isRetryable`이 문구만 다른 비슷한 코드여서 중복이 있다. 공통화는 사용처가 늘 때 REFACTOR에서 하는 편이 안전하다고 보고 이번에는 두지 않았다.
- **돌아가기 링크는 주소의 `projectId` 사용**: 태스크 로딩 전에도 링크를 보여주기 위해서다. 주소의 프로젝트와 태스크의 실제 소속이 다른 경우의 처리는 서버(403/404)에 맡긴다.

## 비고
- 서버가 다른 프로젝트 주소로 접근한 태스크에 어떻게 응답하는지는 브라우저 수동 테스트에서 확인이 필요하다.
- Git 저장소가 아니라 커밋은 없다.
