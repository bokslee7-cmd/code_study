# TASK-054. Dashboard 페이지 (프로젝트 목록)

## 상태
완료

## 날짜
2026-11-10

## 작업 요약
로그인 직후 가장 먼저 보는 **대시보드**를 자리표시자("대시보드" 제목만 있던 페이지)에서 실제 프로젝트 목록 화면으로 바꿨다. 가게 입구의 진열대처럼, 들어오면 내 프로젝트들이 최근 활동 순으로 카드로 늘어서 있다.

| 상황 | 화면 |
|------|------|
| 불러오는 중 | `프로젝트를 불러오는 중입니다...` (`role="status"`) |
| 성공 | 프로젝트 카드 그리드 (모바일 1열, 태블릿 2열, 데스크톱 3열). 서버가 준 순서(최근 활동 순)를 그대로 유지 |
| 빈 목록 | `아직 프로젝트가 없습니다.` 안내 (만들기 버튼은 T056에서 연결) |
| 실패 | 서버가 준 한국어 메시지를 알림(`role="alert"`)으로 표시 + **다시 시도** 버튼. 서버 메시지가 없는 오류는 `프로젝트를 불러오지 못했습니다. 잠시 후 다시 시도하세요.` |

서버 상태는 TanStack Query로 관리하며 쿼리 키는 `["projects"]`다.

**함께 처리한 보안 문제 (캐시 정리)**: 이 화면이 앱 최초의 "개인 데이터 캐시"를 만든다. 쿼리 캐시는 로그아웃해도 메모리에 남기 때문에, 같은 브라우저에서 다른 계정이 로그인하면 이전 사용자의 프로젝트 목록이 잠깐 보일 수 있었다. 호텔 객실의 이전 손님 짐이 청소 없이 남아 있는 것과 같다. 그래서 인증 스토어의 토큰이 사라지는 순간(로그아웃 또는 세션 만료) 쿼리 캐시를 전부 비우는 구독을 `queryClient.ts`에 추가했다. 토큰 자동 갱신(토큰 값만 교체)에서는 비우지 않는다.

**라우팅**: `App.tsx`의 `/dashboard` 보호 라우트에 `Dashboard`를 연결했다(`ProtectedRoute` + `AppShell` 안 그대로).

## 변경 파일
- `frontend/src/pages/Dashboard.tsx` (신규)
- `frontend/src/lib/queryClient.ts`: 토큰이 사라지면 `queryClient.clear()` 하는 인증 스토어 구독 추가
- `frontend/src/App.tsx`: `/dashboard` 라우트 element를 `<Dashboard />`로 교체
- `frontend/tests/unit/Dashboard.test.tsx` (신규): 목록 2개 + 상태 4개 케이스 (생성 플로우 6개는 TASK-056)
- `frontend/tests/unit/queryClient-auth.test.ts` (신규): 2개 케이스 (세션 종료 시 캐시 삭제 / 토큰 갱신 시 유지)
- `frontend/tests/unit/App.test.tsx` (**기존 테스트 최소 수정**, 아래 비고 참고)
- `docs/task-reports/TASK-054-Dashboard-페이지-프로젝트-목록.md` (신규): 이 보고서

## TDD 결과
- RED 커밋: 해당 없음(Git 저장소 아님). 구현 전 `Failed to resolve import "../../src/pages/Dashboard"`로 Dashboard 테스트가 실패했고, `queryClient-auth.test.ts`는 `expected [ { id: 'p-1' } ] to be undefined`로 1개 실패(캐시가 남아 있음)하는 것을 직접 확인했다.
- GREEN 커밋: 해당 없음. 구현 후 Dashboard 6개(이 태스크 몫) + queryClient-auth 2개 통과. `App.test.tsx`의 `/dashboard` 라우트 신규 케이스는 연결 전 실패 → 연결 후 통과.
- REFACTOR 커밋: 해당 없음.
- 테스트 커버리지: `Dashboard.tsx` 100%(문장·분기·함수·줄), `queryClient.ts` 100%.

## 기술 결정
- **에러 문구는 `ApiError`일 때만 서버 메시지 사용**: `api-client`는 모든 네트워크/HTTP 오류를 한국어 메시지를 가진 `ApiError`로 바꾼다. 그 외 `Error`(코드 버그 등)의 원문은 사용자에게 노출하지 않고 일반 안내를 보여준다.
- **정렬은 서버를 신뢰**: 서버가 "최근 활동 순"으로 주므로 화면에서 다시 정렬하지 않는다.
- **캐시 정리를 `useAuth().logout`이 아니라 스토어 구독으로**: 로그아웃 버튼 경로뿐 아니라 토큰 갱신 실패로 세션이 정리되는 경로(T038A)도 한 곳에서 커버된다.
- **`Promise.all`/로딩 스켈레톤 없음**: 테스트가 요구하지 않는 장식은 만들지 않았다(YAGNI).

## 비고
- **기존 테스트 수정(`App.test.tsx`) — 사유와 범위**: Dashboard/ProjectDetail이 서버 데이터를 `useQuery`로 불러오게 되어, 기존 테스트의 (1) `QueryClientProvider` 없이 렌더, (2) 동기 `getByRole('heading', '대시보드')`, (3) `/projects/p1`을 "프로젝트 상세"라는 자리표시자 제목으로 찾는 방식이 더는 성립하지 않는다. 그래서 다음만 바꿨다: `QueryClientProvider` 감싸기, 프로젝트 서비스 mock(`listProjects → []`, `getProject → makeProject`), 관련 단언을 `findByRole`로, `/projects/p1`의 기대 제목을 프로젝트 제목("My Todo App")으로. 단언을 약화하거나 삭제한 것은 없고, `/dashboard`가 실제 목록 화면(빈 상태 문구)을 그리는지 확인하는 케이스를 **하나 추가**했다. `App-auth.test.tsx`(비로그인 리다이렉트)는 수정 없이 통과한다.
- 헤더(AppShell)에 대시보드 링크는 아직 없다. 필요해지면 이 틀에 추가하면 된다(TASK-042 비고).
- Git 저장소가 아니라 커밋은 없다.
