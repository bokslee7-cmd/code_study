# TASK-021. Zustand 인증 스토어 (JWT 상태)

## 상태
완료

## 날짜
2026-11-04

## 작업 요약
`frontend/src/stores/auth-store.ts`에 로그인 상태를 담는 Zustand 스토어(`useAuthStore`)를 만들었다. 로그인·회원가입·토큰 갱신 화면이 이 스토어 하나를 보고 "지금 로그인했는가"를 판단한다.

| 항목 | 내용 |
|------|------|
| 상태 | `accessToken`(문자열 또는 null), `user`(`id`, `email`, `skillLevel` 또는 null) |
| 동작 | `setSession`(로그인 성공 시 토큰+사용자 저장), `setAccessToken`(토큰 갱신 시 토큰만 교체), `clearSession`(로그아웃) |
| 선택자 | `selectIsAuthenticated` — 토큰이 있으면 true |
| api-client 연동 | 스토어가 로드될 때 `setAuthTokenProvider`로 토큰 조회 함수를 등록 → 이후 모든 요청에 `Authorization: Bearer <토큰>` 자동 부착 |

비유하면 스토어는 "출입증 보관함"이다. 로그인하면 출입증(토큰)과 명찰(사용자 정보)을 넣고, 로그아웃하면 둘 다 비운다. 우체국 창구(`apiClient`)는 요청을 보낼 때마다 보관함을 들여다보고 출입증이 있으면 붙인다.

### 추가 작업: `/dev-test`에서 스토어 동작 확인
기존 `/dev-test` 라우트의 `DevTestPage`에 "인증 스토어 테스트" 영역(`AuthStoreTest`)을 붙였다. 새 라우트는 만들지 않았다.

| 구성 | 내용 |
|------|------|
| 사용자 정보 컴포넌트 | `useAuthStore`의 `user`를 구독해 JSON 또는 "사용자 없음" 표시 |
| 인증 상태 컴포넌트 | `selectIsAuthenticated`를 구독해 `isAuthenticated: true/false` 표시 |
| "사용자 설정" 버튼 | 테스트 사용자(`dev-test@example.com`)와 가짜 토큰을 `setSession`으로 저장 |
| "인증 초기화" 버튼 | `clearSession` 호출 |

두 표시 컴포넌트는 서로 props를 주고받지 않고 각자 스토어를 직접 구독한다. 그래서 버튼 한 번에 둘이 함께 바뀌면 "스토어 하나를 여러 곳이 공유한다"는 것이 확인된다.

## 변경 파일
- `frontend/src/components/dev/AuthStoreTest.tsx` (신규): 위 영역 컴포넌트
- `frontend/tests/unit/AuthStoreTest.test.tsx` (신규): 초기 화면, 두 버튼 클릭 시 동시 갱신, 스토어 외부 변경 추종, `/dev-test` 라우트 노출 테스트 6개
- `frontend/src/pages/DevTestPage.tsx`: `<AuthStoreTest />` 추가

- `frontend/src/stores/auth-store.ts` (신규): `useAuthStore`, `selectIsAuthenticated`, `AuthUser` 타입, 토큰 공급자 등록
- `frontend/tests/unit/auth-store.test.ts` (신규): 초기 상태, 세션 저장·갱신·삭제, 브라우저 저장소 미사용, api-client 헤더 연동 테스트 8개
- `frontend/src/main.tsx`: 앱 시작 시 `./stores/auth-store`를 불러와 토큰 공급자가 등록되게 함
- `frontend/src/services/api-client.ts`: T021 이전 상태를 가리키던 주석만 현재 구조에 맞게 수정 (동작 변경 없음)
- `specs/001-ai-code-learning-platform/tasks.md`: T021 완료 표시
- `docs/task-reports/TASK-021-Zustand-인증-스토어.md` (신규): 작업 결과 기록

## TDD 결과
- RED 커밋: 해당 없음 (Git 저장소 아님). 구현 전 `auth-store` 모듈 부재로 테스트 파일이 실패하는 것을 확인했다.
- GREEN 커밋: 해당 없음. 구현 후 스토어 8개 + 테스트 영역 6개 통과 (프론트엔드 전체 64개 통과). 테스트 영역도 구현 전에 컴포넌트 모듈 부재로 실패하는 것을 먼저 확인했다.
- REFACTOR 커밋: 해당 없음. 구현이 이미 최소 형태라 구조 변경은 없고, 낡은 주석만 정리했다.
- 테스트 커버리지: `auth-store.ts` 100% (Stmts/Branch/Funcs/Lines), 전체 100%. tsc, eslint, prettier 통과.

## 기술 결정
- **액세스 토큰은 메모리에만 보관, 저장소 persist 없음**: research.md가 정한 방침(JWT는 HttpOnly 쿠키)과 맞추기 위해서다. localStorage에 두면 XSS 공격 시 스크립트가 토큰을 읽을 수 있다. "저장소에 토큰이 남지 않는다"는 테스트로 고정했다. 새로고침하면 스토어가 비므로, 이후 복구는 쿠키의 리프레시 토큰으로 갱신하는 T038이 맡는다.
- **토큰 공급자는 스토어 쪽에서 등록**: T020에서 정한 주입 방식을 그대로 썼다. `api-client`가 스토어를 import하면 서로를 불러 순환 의존이 되므로, 스토어가 `api-client`를 한 방향으로만 import한다.
- **`isAuthenticated`를 상태로 두지 않고 선택자로 계산**: 토큰과 따로 저장하면 두 값이 어긋날 수 있다. 토큰 유무에서 바로 계산해 한 곳만 믿게 했다.
- **`user`는 `skillLevel` 등 camelCase**: 백엔드 `users` 테이블의 `skill_level`은 서비스 계층(T034)에서 변환해 넣는다. 스토어는 화면용 모양만 안다.

## 비고
- 현재 `api-client`에는 `withCredentials`가 없다. 리프레시 토큰 쿠키를 주고받는 설정은 T034/T038에서 인증 API를 붙일 때 함께 추가해야 한다.
- 스토어를 화면에서 쓰는 코드(`useAuth`, `ProtectedRoute`)는 아직 없다. 각각 T038, T037의 범위다.
- 실제 브라우저에서 로그인 흐름을 확인하지는 않았다. 단위 테스트에서 axios 어댑터를 대체해 헤더 부착만 검증했다.
- 요청 문구의 `setUser()`/`clearAuth()`는 실제 스토어의 `setSession()`/`clearSession()`에 해당한다. 이미 테스트로 고정된 이름이라 바꾸지 않았다.
- 테스트 실행 시 `UserDisplay`/`AuthStatusDisplay`의 "not wrapped in act(...)" 경고가 stderr에 나온다. 기존 `DevTestPage` 테스트에도 같은 경고가 있고 통과 여부에는 영향이 없다. 브라우저에서 직접 눌러 보는 확인은 하지 않았다.
- `DevTestPage`와 `AuthStoreTest`는 개발용이다. 배포 전에 함께 제거하거나 개발 모드에서만 노출해야 한다.
- Git 저장소가 아니라 커밋은 없다.
