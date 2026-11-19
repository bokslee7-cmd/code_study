# TASK-042 (보조). 로그아웃 버튼 — AppShell 공통 헤더

## 상태
완료

## 날짜
2026-11-09

## 작업 요약
로그인한 사용자 화면 위쪽에 "내 이메일 + 로그아웃 버튼"이 있는 얇은 띠(헤더)를 만들었다. 건물로 치면 출입구 옆에 "퇴장" 버튼이 하나도 없어서, 들어온 손님이 나가는 길을 확인해 볼 수 없었던 문제를 해결한 것이다.

T042("로그아웃 → 쿠키 삭제 → 로그인 화면 이동")를 브라우저에서 확인하려면 눌러 볼 버튼이 필요한데, 화면 어디에도 없었다. 대시보드는 아직 자리표시자(placeholder)라서, 보호된 페이지 전체를 감싸는 공통 틀 `AppShell`에 넣었다. 나중에 대시보드(T054)가 만들어져도 이 틀은 그대로 쓸 수 있다.

버튼을 누르면 `useAuth().logout()`이 동작한다: 서버에 로그아웃 요청(쿠키 폐기) → 성공/실패와 무관하게 로컬 세션 정리 → `/login`으로 이동.

## 변경 파일
- `frontend/src/components/layout/AppShell.tsx` (신규): 헤더(이메일, 로그아웃 버튼) + `<Outlet />`
- `frontend/src/App.tsx`: 보호 라우트(`/dashboard`, `/projects/...`, `/trash`)를 `AppShell` 레이아웃 라우트로 한 겹 더 감쌈
- `frontend/tests/unit/AppShell.test.tsx` (신규): 3개 케이스(이메일·버튼·하위 페이지 표시, 버튼 클릭 시 서버 요청+세션 정리+이동, 서버 실패해도 로컬 정리+이동)
- `docs/task-reports/TASK-042-로그아웃-버튼-AppShell.md` (신규): 이 보고서

## TDD 결과
- RED 커밋: 해당 없음(Git 저장소 아님). 구현 전 `components/layout/AppShell` 모듈이 없어 import 실패하는 것을 확인했다.
- GREEN 커밋: 해당 없음. 구현 후 새 테스트 3개 포함 전체 202개 통과.
- REFACTOR 커밋: 해당 없음.
- 기존 테스트는 수정하지 않았다(`App.test.tsx` 포함 그대로 통과). tsc, eslint, prettier 통과.
- 브라우저 확인: 버튼 클릭 → `POST /auth/logout` 204 → `/login` 이동 확인(TASK-039 보고서).

## 기술 결정
- **`ProtectedRoute` 안이 아니라 별도 `AppShell` 레이아웃**: `ProtectedRoute`는 "로그인했는가"만 판단하는 경비 역할이고, 화면 틀은 다른 책임이라 분리했다. `ProtectedRoute` 테스트도 건드리지 않았다.
- **헤더에는 제목(h1/h2)을 넣지 않음**: 페이지 제목이 하나만 있어야 하고, 기존 `App.test.tsx`가 제목으로 페이지를 식별하기 때문이다.
- **디자인은 최소한**: 기존 `Button`(shadcn)과 Tailwind 유틸리티만 썼다. 본격적인 네비게이션(대시보드 링크, 휴지통 링크 등)은 Dashboard 구현(T054, T182) 때 이 틀에 추가하면 된다.

## 비고
- 이 작업은 `tasks.md`에 별도 항목이 없는 보조 작업이다. T042를 검증하려고 사용자가 "Chrome 확장으로 진행 + 버튼 UI 먼저 추가"를 선택해 진행했다.
- Git 저장소가 아니라 커밋은 없다.
