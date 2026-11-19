# TASK-032. RegisterForm 컴포넌트

## 상태
완료

## 날짜
2026-11-09

## 작업 요약
도서관 회원증을 만들 때 쓰는 "신청서 양식"을 화면에 만들었다. 이메일, 비밀번호, 비밀번호 확인 세 칸을 채우고 "회원가입" 버튼을 누르면, 접수 창구에 내기 전에 양식 자체의 빈칸과 오타를 먼저 검사한다.

| 상황 | 화면 반응 |
|------|-----------|
| 이메일이 비었거나 `a@b.co` 형식이 아님 | 이메일 칸 아래에 안내, 제출하지 않음 |
| 비밀번호가 8자 미만 | "비밀번호는 8자 이상이어야 합니다." |
| 비밀번호 확인이 다름 | 확인 칸 아래에 "비밀번호가 일치하지 않습니다." |
| 검증 통과 | 이메일 앞뒤 공백을 지운 `{email, password}`만 `onSubmit`에 전달(확인 칸 값은 서버에 보내지 않음) |
| 제출 중 | 버튼이 비활성화되고 "가입 중..."으로 바뀜(중복 제출 방지) |
| 서버가 거절(예: 중복 이메일) | 서버가 준 한국어 메시지를 `role="alert"`로 표시, 버튼 다시 활성화 |

폼은 "제출하면 무엇을 할지"를 모른다. `onSubmit(values) => Promise<void>`만 받고, 가입 API 호출과 화면 이동은 페이지(T035)가 맡는다. 폼은 입력과 검증과 상태 표시만 책임진다.

## 변경 파일
- `frontend/src/components/auth/RegisterForm.tsx` (신규)
- `frontend/src/components/auth/FormField.tsx` (신규): 라벨 + 입력 + 오류 문구 묶음. 로그인/회원가입 폼이 공유
- `frontend/src/components/auth/useSubmitState.ts` (신규): "제출 중 / 서버 오류" 상태. 두 폼이 공유
- `frontend/src/lib/auth-validation.ts` (신규): 이메일/비밀번호 검증 함수. 두 폼이 공유
- `frontend/tests/unit/RegisterForm.test.tsx` (신규): 8개 케이스
- `frontend/tests/unit/auth-validation.test.ts` (신규): 13개 케이스

## TDD 결과
- RED 커밋: 해당 없음(Git 저장소 아님). 구현 전 `RegisterForm`, `auth-validation` 모듈이 없어 import 실패로 테스트 파일이 실행조차 되지 않는 것을 확인했다.
- GREEN 커밋: 해당 없음. 구현 후 두 파일 21개 모두 통과.
- REFACTOR 커밋: 해당 없음. 로그인 폼(T033)을 만들 때 겹치는 부분을 `FormField`, `useSubmitState`, `auth-validation`으로 뽑아 두었다.
- 테스트 커버리지: `RegisterForm.tsx`, `FormField.tsx`, `auth-validation.ts` 줄 100%.

## 기술 결정
- **react-hook-form/zod를 쓰지 않음**: `package.json`에 설치돼 있지 않다. 필드가 3개뿐인 폼 때문에 의존성을 늘리지 않고 `useState`로 직접 구현했다(YAGNI).
- **검증은 제출할 때 한 번**: 글자를 칠 때마다 빨간 글씨가 뜨면 입력 중인 사람을 재촉하는 느낌이 든다. 제출 시점에 한꺼번에 알려준다.
- **최소 비밀번호 길이 8자**: `backend/src/utils/security.py`의 `MIN_PASSWORD_LENGTH = 8`과 같은 값이다. 상수에 "백엔드와 같은 값이어야 한다"는 주석을 남겼다.
- **접근성**: 모든 입력에 `label`, 오류가 있으면 `aria-invalid`와 `aria-describedby`로 오류 문구를 연결, 서버 오류는 `role="alert"`.
- **서버 오류 메시지는 `error.message` 그대로 표시**: api-client 인터셉터가 `ApiError`로 바꿔 주고, 서버 메시지는 이미 한국어다.

## 비고
- `details.field`(서버가 400에서 알려주는 문제 필드)를 해당 입력 칸 아래에 붙이는 기능은 하지 않았다. 클라이언트 검증이 같은 규칙을 먼저 걸러 주므로 서버 400이 오는 경우는 드물다. 필요해지면 확장한다.
- 테스트 실행 시 `act(...)` 경고가 출력된다. 기존 T021 테스트(AuthStoreTest)에도 똑같이 나오는 환경 문제로, RTL(`@testing-library/dom` 9.x)과 user-event(10.x)가 서로 다른 dom 라이브러리를 쓰기 때문이다. 테스트 결과에는 영향이 없다. 별도 정리 대상으로 남긴다.
- Git 저장소가 아니라 커밋은 없다.
