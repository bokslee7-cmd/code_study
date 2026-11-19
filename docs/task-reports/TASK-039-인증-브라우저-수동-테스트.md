# TASK-039 ~ 042. 인증 흐름 브라우저 수동 테스트

## 상태
완료 (T039, T040, T041, T042 모두 통과)

## 날짜
2026-11-09

## 작업 요약
실제 PostgreSQL(개발 DB `codelearning`), 백엔드(`localhost:8000`), 프런트엔드(`localhost:5173`)를 모두 띄우고 Chrome에서 인증 흐름을 손님처럼 한 번씩 돌려 봤다. "문 앞 경비 → 회원 등록 → 출입증 발급 → 퇴장 처리" 순서다.

도구는 **Claude in Chrome 확장**을 썼다. 요청은 Playwright MCP였지만 이 세션에는 연결돼 있지 않아서, 사용자가 확인한 뒤 Chrome 확장으로 진행했다.

테스트는 두 차례 했다.
- 1차: 로그아웃 버튼이 없어서 T042만 절반(직접 `fetch`로 로그아웃 요청)만 확인했다.
- 2차(최종): 로그아웃 버튼(`AppShell`, TASK-042 보고서 참고)을 추가한 뒤 T039~T042를 다시 확인했다. 아래 표는 2차 결과다.

| 태스크 | 확인한 것 | 결과 |
|--------|-----------|------|
| T042 | 대시보드의 **로그아웃 버튼 클릭** | `POST /auth/logout` 204, `/login`으로 이동, 쿠키 삭제 확인(`refresh` 401), 이후 `/dashboard` 재접근도 `/login`으로 이동 |
| T041 | 비로그인으로 `/dashboard` 접근 | `/login`으로 이동 |
| T039 | 새 계정으로 회원가입 | `POST /auth/register` 201, 가입 완료 안내와 함께 `/login`으로 이동 |
| T040 | 로그인 | `POST /auth/login` 200, `/dashboard` 진입, 헤더에 이메일과 로그아웃 버튼 표시. 리프레시 토큰은 `document.cookie`에 보이지 않음(HttpOnly), `localStorage`·`sessionStorage` 비어 있음 |
| (T038 보강, 1차) | 로그인 상태로 새로고침 | `refresh` 200 → `me` 200, 로그인 유지 |

## 변경 파일
- `specs/001-ai-code-learning-platform/tasks.md`: T039~T042 완료 표시
- `docs/task-reports/TASK-039-인증-브라우저-수동-테스트.md`: 이 보고서
- 이 태스크 자체의 코드 변경은 없다(로그아웃 버튼 추가는 TASK-042 보고서).

## TDD 결과
해당 없음(수동 테스트 태스크). 테스트 직전 프런트 vitest 202개, 백엔드 pytest 339개가 모두 통과한 상태였다.

## 기술 결정
- 프런트-백엔드 간 쿠키 교환(CORS preflight, `withCredentials`, `SameSite=Strict`)이 `localhost:5173 -> localhost:8000`에서 실제로 동작함을 브라우저 네트워크 기록으로 확인했다.
- 백엔드는 `.env` 없이 환경변수(`DATABASE_URL`, `JWT_SECRET_KEY`, `ALLOWED_ORIGINS`, `COOKIE_SECURE=false`)로 기동했다. JWT 비밀키는 실행 때마다 새로 만든 임시 값이라, 서버를 재시작하면 기존 토큰은 무효가 된다.
- 순서를 T042 → T041 → T039 → T040으로 바꿨다. 같은 Chrome 프로필에 이미 로그인 세션(쿠키)이 남아 있어 T041(비로그인 상태)의 전제가 맞지 않았고, 이 세션을 로그아웃 버튼으로 끝내는 것이 T042 확인을 겸했기 때문이다.

## 비고
- 개발 DB에 테스트 계정 `browser-test@example.com`, `browser-test2@example.com`이 남아 있다. 비밀번호는 `.env.example`의 `TEST_USER_PASSWORD`와 같다.
- 시도하지 않은 것: 401 시 자동 갱신 재시도(T038A)의 브라우저 확인. 보호된 데이터 API를 부르는 화면이 아직 없어 Phase 4 이후에 가능하다.
- Git 저장소가 아니라 커밋은 없다.
