# TASK-036. Login 페이지

## 상태
완료

## 날짜
2026-11-09

## 작업 요약
"로그인 창구"를 하나의 화면으로 완성했다. 확인대(`LoginForm`, T033)와 우체부(`login`, T034)를 연결하고, 통과하면 출입증(액세스 토큰)을 사물함(auth-store)에 넣은 뒤 원래 가려던 곳으로 안내한다.

| 상황 | 동작 |
|------|------|
| 로그인 성공 | `useAuthStore.setSession({accessToken, user, expiresIn})` 후 이동 |
| 이동 위치 | 보호된 페이지에서 튕겨 왔다면 그 원래 위치(`state.from`, 쿼리 포함), 아니면 `/dashboard` |
| 로그인 실패 | 이동하지 않음, 세션 저장 안 함, 폼이 서버 메시지 표시 |
| 가입 직후 도착 | "회원가입이 완료되었습니다. 로그인해 주세요." 안내(`role="status"`) |
| 하단 | "계정이 없으신가요? 회원가입" 링크 -> `/register` |

액세스 토큰은 메모리(auth-store)에만 있고 `localStorage`에는 쓰지 않는다. 기존 설계 그대로다.

## 변경 파일
- `frontend/src/pages/Login.tsx` (신규)
- `frontend/tests/unit/Login.test.tsx` (신규): 6개 케이스
- `frontend/src/stores/auth-store.ts`: `setSession`이 `expiresIn`(선택)을 받도록 확장 (TASK-038 항목 참고)
- `frontend/src/App.tsx`: `/login` 라우트를 `Login`으로 교체

## TDD 결과
- RED 커밋: 해당 없음(Git 저장소 아님). 구현 전 `pages/Login` 모듈이 없어 import 실패를 확인했다.
- GREEN 커밋: 해당 없음. 구현 후 6개 모두 통과.
- REFACTOR 커밋: 해당 없음.
- 테스트 커버리지: `Login.tsx` 줄 100%, 분기 90.9%(`state.from.search`가 없을 때의 `?? ''` 쪽 분기 하나. 실제 라우터는 항상 `search`를 채워 주므로 방어용이다).

## 기술 결정
- **`expiresIn`을 스토어에 함께 저장**: 자동 갱신(T038)이 "언제 갱신할지" 알려면 서버가 준 유효 시간이 필요하다. 로그인 시점에 전달해 두면 타이머가 스토어만 보고 움직인다.
- **원래 위치로 복귀**: `ProtectedRoute`가 `state.from`에 현재 위치를 실어 보내고, 로그인 페이지가 그 위치로 되돌려 준다. `from.search`까지 이어 붙여 쿼리 문자열도 보존한다. 지침의 "복귀하면 좋음"을 반영했고, 코드는 몇 줄뿐이다.
- **이미 로그인한 사람이 `/login`에 들어와도 자동 이동하지 않음**: 요구되지 않았다(YAGNI).
- 헤딩 이름은 정확히 "로그인"이다(제출 버튼도 "로그인"이지만 버튼은 heading 역할이 아니라 겹치지 않는다).

## 비고
- 대시보드의 로그아웃 버튼은 아직 없다(대시보드는 placeholder). `useAuth().logout`만 준비해 두었다(TASK-038).
- Git 저장소가 아니라 커밋은 없다.
