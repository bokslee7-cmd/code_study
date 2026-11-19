# TASK-037. ProtectedRoute (라우트 보호)

## 상태
완료 (단, 기존 `App.test.tsx` 5개 케이스와 충돌 - 비고 참고)

## 날짜
2026-11-09

## 작업 요약
화면 쪽 "출입문 경비원"을 세웠다. 백엔드 경비원(`get_current_user`, TASK-027)이 API 앞을 지킨다면, 이 경비원은 페이지 앞을 지킨다. 대시보드, 프로젝트, 휴지통 앞에 서서 출입증이 있는지 본다.

| 경비원이 보는 상황 | 하는 일 |
|--------------------|---------|
| 출입증(액세스 토큰) 있음 | 통과: 안쪽 페이지(`<Outlet />`) 표시 |
| 출입증 없음 + 세션 복구 진행 중 | 판단 보류: "로그인 상태를 확인하는 중입니다..."(`role="status"`) |
| 출입증 없음 + 복구 끝남 | `/login`으로 돌려보냄(`replace`), 원래 위치를 `state.from`에 담아 줌 |

"복구 진행 중 보류"가 핵심이다. 새로고침하면 메모리의 토큰이 사라지고 쿠키로 되살리는 데 잠깐 걸린다. 그 짧은 순간에 경비원이 "증이 없네요" 하고 로그인 화면으로 보내 버리면, 이미 로그인한 사람이 깜빡이며 튕겼다 돌아오게 된다. 그래서 복구가 끝날 때까지 기다린다.

`App.tsx`는 보호 대상 라우트(`/dashboard`, `/projects/:projectId`, `/projects/:projectId/tasks/:taskId`, `/trash`)를 `<Route element={<ProtectedRoute />}>` 아래에 묶었다. `/`는 `/dashboard`로 이동하므로 같은 경비를 거친다. `/login`, `/register`, `/dev-test`, 404는 보호하지 않는다.

## 변경 파일
- `frontend/src/components/auth/ProtectedRoute.tsx` (신규)
- `frontend/src/App.tsx`: 로그인/회원가입 라우트를 실제 페이지로 교체, 보호 대상 라우트를 `ProtectedRoute` 레이아웃 라우트로 묶음, `useAuthSession()` 호출 추가
- `frontend/tests/unit/ProtectedRoute.test.tsx` (신규): 4개 케이스
- `frontend/tests/unit/App-auth.test.tsx` (신규): 9개 케이스. 비로그인 시 5개 보호 경로가 로그인으로 이동, `/login`·`/register`·`/dev-test`는 공개, 복구 중 로딩 표시, 새로고침 후 쿠키 복구 시 원래 페이지 표시

## TDD 결과
- RED 커밋: 해당 없음(Git 저장소 아님). 구현 전 `ProtectedRoute` 모듈이 없어 import 실패를 확인했다.
- GREEN 커밋: 해당 없음. 새 테스트(`ProtectedRoute` 4개, `App-auth` 9개) 모두 통과.
- REFACTOR 커밋: 해당 없음.
- 테스트 커버리지: `ProtectedRoute.tsx`, `App.tsx` 100%.

## 기술 결정
- **`children` 래퍼가 아니라 레이아웃 라우트(`Outlet`)**: 라우트 네 개를 `<ProtectedRoute>`로 일일이 감싸는 대신 한 번에 묶을 수 있어서 보호 누락 실수가 줄어든다.
- **판단 순서는 "토큰 있음 -> 복구 중 -> 리다이렉트"**: 복구 중에 사용자가 로그인 페이지에서 직접 로그인에 성공했다면 로딩을 보여 줄 이유가 없다.
- **로딩 UI는 최소(문장 하나)**: 스켈레톤이나 스피너는 요구되지 않았다.

## 비고
- **기존 `frontend/tests/unit/App.test.tsx`를 사용자 승인 하에 수정했다 ("테스트는 불변" 규칙의 예외).** 아래 충돌 때문에 구현 에이전트는 파일을 건드리지 않았고, 오케스트레이터가 사용자에게 선택지를 물어 "테스트에 로그인 세션 주입" 안을 승인받아 적용했다. 수정은 `beforeEach`/`afterEach`에서 인증 세션을 심고 `auth-service`를 `vi.mock` 하는 것뿐이며, 각 케이스의 기대값(경로 → 제목)은 그대로다. 적용 후 전체 182개 통과. 충돌 내용은 다음과 같다. 이 테스트는 비로그인 상태에서 `/dashboard`, `/projects/p1`, `/projects/p1/tasks/t1`, `/trash`, `/`가 각각 "대시보드/프로젝트 상세/태스크 상세/휴지통" 제목을 그대로 렌더링한다고 기대한다. 이 경로들을 `ProtectedRoute`로 감싸는 것이 이번 요구사항이므로, 비로그인 상태에서는 로그인 페이지로 가는 것이 올바른 동작이고 두 요구가 서로 양립할 수 없다. "구현을 고쳐서 통과시키라"는 지침을 지킬 방법이 없었고(보호를 풀면 요구사항 자체를 어긴다), 테스트를 약화하지 말라는 지침도 있어서 파일을 건드리지 않았다. 해결안은 `App.test.tsx`에서 보호 경로 5개 케이스만 `beforeEach`로 인증된 세션(`useAuthStore.setState({isRestoring:false})` + `setSession`)을 심고 `auth-service`를 `vi.mock` 하도록 고치는 것이다. 오케스트레이터 승인이 필요하다. 그동안 `App-auth.test.tsx`가 새 라우팅 동작(보호/공개/복구)을 대신 검증한다.
- 비로그인 시 보호/리다이렉트 동작은 `App-auth.test.tsx`가 검증하고, `App.test.tsx`는 "경로 → 페이지 연결"만 확인한다.
- Git 저장소가 아니라 커밋은 없다.
