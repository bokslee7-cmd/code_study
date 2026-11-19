# TASK-035. Register 페이지

## 상태
완료

## 날짜
2026-11-09

## 작업 요약
"회원가입 창구"를 하나의 화면으로 완성했다. 신청서 양식(`RegisterForm`, T032)과 우체부(`register`, T034)를 연결하고, 접수가 끝나면 로그인 창구로 안내한다.

흐름은 이렇다.
1. 사용자가 양식을 채워 제출한다.
2. 페이지가 `register({email, password})`를 호출한다.
3. 성공하면 `/login`으로 이동한다. 이때 `state: { registered: true }`를 함께 보내서 로그인 화면이 "회원가입이 완료되었습니다. 로그인해 주세요." 안내를 보여 준다.
4. 실패하면(예: 중복 이메일 409) 이동하지 않고, 폼이 서버 메시지를 그 자리에서 보여 준다.

백엔드 계약상 가입 응답에는 토큰이 없다. 그래서 가입 직후 자동 로그인은 하지 않고 로그인 화면으로 보낸다.

화면 틀(제목 h1, 안내 문구, 폼, 하단 링크)은 로그인 페이지와 똑같아서 `AuthCard`로 뽑아 공유했다. 하단에는 "이미 계정이 있으신가요? 로그인" 링크가 있다.

## 변경 파일
- `frontend/src/pages/Register.tsx` (신규)
- `frontend/src/components/auth/AuthCard.tsx` (신규): 로그인/회원가입 공용 화면 틀
- `frontend/tests/unit/Register.test.tsx` (신규): 3개 케이스 (`auth-service`를 `vi.mock`으로 대체)
- `frontend/src/App.tsx`: `/register` 라우트를 `Register`로 교체 (TASK-038에서 함께 정리)

## TDD 결과
- RED 커밋: 해당 없음(Git 저장소 아님). 구현 전 `pages/Register` 모듈이 없어 import 실패를 확인했다.
- GREEN 커밋: 해당 없음. 구현 후 3개 모두 통과.
- REFACTOR 커밋: 해당 없음. 공통 틀 `AuthCard`는 로그인 페이지(T036)와 함께 만들었다.
- 테스트 커버리지: `Register.tsx`, `AuthCard.tsx` 100%.

## 기술 결정
- **`navigate(..., { replace: true })`**: 가입이 끝난 뒤 뒤로 가기를 눌러 이미 제출한 가입 양식으로 돌아오는 일을 막는다.
- **안내는 URL 쿼리가 아닌 라우터 `state`로 전달**: 주소창에 `?registered=1`이 남지 않고, 새로고침하면 안내가 사라져 한 번만 보여 준다.
- **가입 후 자동 로그인 없음**: 계약에 토큰이 없고, 이메일/비밀번호를 한 번 더 입력하게 하는 것이 단순하다.
- 헤딩 이름은 정확히 "회원가입"이어야 기존 `App.test.tsx`의 `/register` 케이스가 통과한다(실제로 통과).

## 비고
- `App.tsx`의 최종 변경 내용과 기존 `App.test.tsx` 충돌 건은 TASK-037, TASK-038 보고서에 정리했다.
- Git 저장소가 아니라 커밋은 없다.
