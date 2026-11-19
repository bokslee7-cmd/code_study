# TASK-052. CreateProjectModal 컴포넌트

## 상태
완료

## 날짜
2026-11-10

## 작업 요약
"새 프로젝트 만들기" **팝업 입력창**을 만들었다. 은행 창구에서 신청서를 쓰는 것과 같다. 신청서 양식(제목·설명)을 채우고 "만들기"를 누르면, 창구 직원이 서류를 먼저 훑어보고(클라이언트 검증), 문제가 없으면 접수(서버 요청)한다. 접수 중에는 같은 서류를 두 번 내밀지 못하게 창구 버튼이 잠긴다.

| 항목 | 동작 |
|------|------|
| 제목(필수) | 앞뒤 공백을 지운 뒤 1~255자. 비었으면 "프로젝트 제목을 입력하세요.", 256자 이상이면 "프로젝트 제목은 255자 이하로 입력하세요." |
| 설명(선택) | 앞뒤 공백을 지우고, 비었으면 `null`로 보냄 |
| 제출 중 | 버튼이 "만드는 중..."으로 바뀌고 비활성화, 취소 버튼 비활성화, Enter 재제출 무시, ESC/바깥 클릭으로 닫히지 않음 |
| 서버가 제목 오류(400, `details.field = "title"`) | 팝업을 닫지 않고 **제목 입력란 아래에** 서버 메시지 표시 |
| 그 밖의 서버/네트워크 오류 | 팝업 안에 알림(`role="alert"`)으로 표시, 닫지 않음 |
| 성공 | 팝업을 닫음 (목록 갱신은 호출한 화면 몫 — T056) |

접근성: `role="dialog"`, `aria-modal="true"`, 제목(`새 프로젝트 만들기`)과 연결, 입력란은 라벨 연결, 열리면 제목 입력란에 포커스, ESC로 닫기, Tab 포커스가 팝업 밖으로 나가지 않음.

## 변경 파일
- `frontend/src/components/project/CreateProjectModal.tsx` (신규)
- `frontend/src/lib/project-validation.ts` (신규): `validateProjectTitle`, `MAX_PROJECT_TITLE_LENGTH`
- `frontend/src/components/ui/textarea.tsx` (신규): shadcn 표준 Textarea (설명 입력란용, 기존 Input과 같은 스타일)
- `frontend/tests/unit/CreateProjectModal.test.tsx` (신규): 15개 케이스
- `frontend/tests/unit/project-validation.test.ts` (신규): 5개 케이스
- `docs/task-reports/TASK-052-CreateProjectModal-컴포넌트.md` (신규): 이 보고서

## TDD 결과
- RED 커밋: 해당 없음(Git 저장소 아님). 구현 전 `CreateProjectModal`, `project-validation` 모듈이 없어 테스트 파일이 실패하는 것을 직접 확인했다.
- GREEN 커밋: 해당 없음. 구현 후 모달 15개 + 검증 5개 통과.
- REFACTOR 커밋: 해당 없음. 기존 `FormField`, `useSubmitState`를 그대로 재사용했다(새 폼 로직을 만들지 않음). 서버 제목 오류만 `useSubmitState`로 흘려보내지 않고 필드 오류로 가로채도록 얇게 감쌌다.
- 포커스 복귀는 T056(Dashboard) 테스트에서 검증한다(아래 기술 결정 참고).
- 테스트 커버리지: `project-validation.ts` 100%, `textarea.tsx` 100%, `CreateProjectModal.tsx` 문장·줄·함수 100%(분기 한 곳, "열기 전 포커스가 HTML 요소가 아닌 경우"만 미검증).

## 기술 결정
- **Radix Dialog 사용(새 라이브러리 아님)**: 이미 `package.json`에 있는 `radix-ui`의 `Dialog`를 썼다. 포커스 가두기, ESC, 배경 스크린리더 숨김을 직접 구현하면 놓치는 경우가 많기 때문이다. Radix는 `aria-modal`을 직접 붙이지 않아 `aria-modal="true"`를 명시했다.
- **제출 중 닫힘 방지**: 요청이 날아가는 중에 팝업이 닫히면 사용자가 결과(성공/실패)를 볼 수 없다. ESC·바깥 클릭·취소 버튼 모두 제출 중에는 막았다.
- **서버 제목 오류 판별 기준**: `ApiError` 이면서 `details.field === 'title'`. 계약상 이 경우만 필드 오류로 보여주고, 나머지는 일반 오류 알림으로 보낸다.
- **포커스 복귀를 직접 구현**: Radix 모달은 닫힐 때 포커스를 `Dialog.Trigger`에게만 돌려준다. 우리는 Trigger 없이 상위 화면의 상태로 열고 닫으므로, 열릴 때의 활성 요소(`document.activeElement`)를 기억했다가 `onCloseAutoFocus`에서 돌려준다. (처음엔 이 부분 없이 구현했다가 T056 테스트에서 포커스가 `body`로 가는 것을 발견해 고쳤다.)
- **설명 글자 수 제한은 두지 않음**: API 계약에 설명 길이 제한이 없어서 클라이언트에서 임의로 만들지 않았다.

## 비고
- 테스트 실행 중 `Warning: An update to CreateProjectModal inside a test was not wrapped in act(...)` 경고가 다수 출력된다. 기존 Register/Login 테스트에서도 같은 종류의 경고가 이미 나오던 환경 잡음이며, 테스트 결과(통과)에는 영향이 없다.
- Git 저장소가 아니라 커밋은 없다.
