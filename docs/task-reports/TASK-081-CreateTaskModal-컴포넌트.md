# TASK-081. CreateTaskModal 컴포넌트

## 상태
완료

## 날짜
2026-11-16

## 작업 요약
"새 태스크 만들기" **팝업**을 만들었다. 제목·설명을 적고, 코드를 올리는 세 가지 방법(파일 / 폴더 / 코드 붙여넣기) 중 탭 하나를 골라 올린다. 택배 접수서에서 보내는 방법을 고르는 것과 같다.

| 항목 | 동작 |
|------|------|
| 입력 | `태스크 제목`(trim 후 5자 이상), `설명 (선택)`(500자 이하) |
| 업로드 탭 | `파일`(FileUpload) / `폴더`(FolderUpload) / `코드 붙여넣기`(PasteCode), 기본은 파일. Radix Tabs(방향키·aria 처리). 탭을 오가도 각 방식에서 고른 내용은 유지 |
| 제출 | 검증을 모두 통과해야 `onSubmit({title, description\|null, uploadMethod, files \| code+language})` 호출, 성공하면 `onClose()` |
| 오류 | 입력 오류는 해당 필드/업로드 영역 아래, 서버 오류(`ApiError.message`)는 모달 안 `role="alert"`로 표시하고 닫지 않음 |
| 제출 중 | 버튼 `만드는 중...`, 취소·탭·업로드 입력 비활성, ESC·바깥 클릭으로 닫히지 않음 |

Dialog 접근성(포커스 가두기, 열기 전 요소로 포커스 복귀 등)은 CreateProjectModal과 같은 방식이다.

## 변경 파일
- `frontend/src/components/task/CreateTaskModal.tsx` (신규)
- `frontend/tests/unit/CreateTaskModal.test.tsx` (신규): 14개
- `docs/task-reports/TASK-081-CreateTaskModal-컴포넌트.md` (신규)

## TDD 결과
- RED 커밋: 해당 없음(Git 저장소 아님). 테스트를 먼저 작성했으나 이 모달 테스트만 구현 전 단독 RED 실행은 하지 않았다(의존 컴포넌트 T076~T080은 이미 RED→GREEN을 거친 상태였다).
- GREEN 커밋: 해당 없음. 구현 후 14개 통과(첫 실행부터 통과).
- REFACTOR 커밋: 해당 없음.
- 테스트 커버리지: 전체 커버리지 실행에서 `All files` 문장 99.9%/분기 97.9%. 이 파일의 개별 수치는 별도 기록하지 않았다.

## 기술 결정
- **상태는 모달이 소유**: 업로드 컴포넌트를 controlled로 만들어 탭 전환으로 unmount돼도 선택이 유지된다.
- **업로드 검증은 제출 시 한 번 더**: 업로드 컴포넌트가 추가 시점에 즉시 검증하지만, "파일을 하나도 안 골랐음"과 "언어 미선택" 같은 제출 시점 오류는 모달이 `validateUploadFiles`/`validatePaste`로 보여준다.
- **성공 토스트는 만들지 않음**: 프로젝트에 토스트 컴포넌트가 아직 없고 이번 테스트가 요구하지 않았다(addendum의 "태스크가 생성되었습니다" 토스트는 후속 과제).

## 비고
- 테스트 실행 중 Radix Tabs/Dialog 때문에 `not wrapped in act(...)` 경고가 출력된다. 기존 CreateProjectModal·Dashboard 테스트에서도 같은 경고가 나오는 기존 환경 이슈이며 실패는 아니다.
- Git 저장소가 아니라 커밋은 없다.
