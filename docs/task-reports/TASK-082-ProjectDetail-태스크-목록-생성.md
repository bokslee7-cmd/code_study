# TASK-082. ProjectDetail 태스크 목록·생성

## 상태
완료

## 날짜
2026-11-16

## 작업 요약
프로젝트 상세 페이지의 "준비 중" 쪽지를 떼고 **실제 태스크 타임라인**을 붙였다. 목차에 챕터(태스크)가 번호순으로 쌓이고, `새 태스크` 버튼으로 새 챕터를 추가한다.

| 상태 | 화면 |
|------|------|
| 로딩 | `태스크를 불러오는 중입니다...` |
| 목록 | 번호 순서대로 `TaskCard` |
| 비어 있음 | `아직 태스크가 없습니다. 첫 태스크를 만들어 보세요.` |
| 오류 | 서버 메시지(없으면 `태스크를 불러오지 못했습니다. 잠시 후 다시 시도하세요.`) + `다시 시도` |

`새 태스크` → `CreateTaskModal` → `createTask` 성공 시 `["projects"]` 쿼리 전체를 무효화(프로젝트 정보의 태스크 수·진행률과 목록 모두 갱신)하고 방금 만든 **태스크 상세 페이지로 이동**한다(requirements-addendum의 "태스크 생성 후 태스크 상세로 이동"). 실패하면 모달에 오류가 남고 이동하지 않는다. 쿼리 키는 `["projects", projectId, "tasks"]`다.

## 변경 파일
- `frontend/src/pages/ProjectDetail.tsx`: `TaskTimeline` 섹션 추가
- `frontend/tests/unit/ProjectDetail.test.tsx`: 기존 "준비 중" placeholder 단언을 "태스크 타임라인" 제목 단언으로 교체하고 task-service mock 추가, 신규 9개 케이스(타임라인 6 + 생성 3). 총 19개
- `frontend/tests/unit/App.test.tsx`: task-service mock 추가(프로젝트 상세가 태스크 목록을 불러오므로), 태스크 상세 라우트 기대값을 `Add Todo Function` 제목으로 갱신(TASK-083)
- `docs/task-reports/TASK-082-ProjectDetail-태스크-목록-생성.md` (신규)

## TDD 결과
- RED 커밋: 해당 없음(Git 저장소 아님). 구현 전 신규 케이스가 `Unable to find role="link"...` 등으로 실패하는 것을 확인했다(ProjectDetail·App·TaskDetail 합쳐 10개 실패, TaskDetail 파일은 import 실패).
- GREEN 커밋: 해당 없음. 구현 후 ProjectDetail 19개 통과, 전체 360개 통과.
- REFACTOR 커밋: 해당 없음.
- 테스트 커버리지: `ProjectDetail.tsx`는 전체 커버리지 실행에서 하락 없이 통과(문장 100%에 준함, 개별 수치는 표에서 별도 기록하지 않음).

## 기술 결정
- **태스크 섹션을 프로젝트 정보가 로드된 뒤에만 그림**: 프로젝트가 403/404면 태스크 요청도 불필요하고 오류 영역이 겹치지 않는다. 같은 파일의 `TaskTimeline` 컴포넌트로 분리해 모달·뮤테이션 상태를 격리했다.
- **쿼리 키를 `["projects", id, "tasks"]`로 중첩**: `["projects"]` 한 번의 무효화로 목록·상세·태스크가 함께 갱신된다.
- **기존 테스트 수정 근거**: 기존 단언("태스크 타임라인은 준비 중입니다.")은 TASK-055가 명시한 임시 문구로 이 태스크가 대체하는 동작이라 교체했다. 나머지 기존 케이스는 그대로 통과한다.

## 비고
- Git 저장소가 아니라 커밋은 없다.
