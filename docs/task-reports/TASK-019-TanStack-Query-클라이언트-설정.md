# TASK-019. TanStack Query 클라이언트 설정

## 상태
완료

## 날짜
2026-11-03

## 작업 요약
`frontend/src/lib/queryClient.ts`에 앱 전체가 공유할 TanStack Query 클라이언트(`queryClient`)와 재시도 판단 함수(`shouldRetry`)를 만들었다. `main.tsx`에서 `QueryClientProvider`로 앱을 감싸, 이후 화면과 API 서비스에서 `useQuery`/`useMutation`을 바로 쓸 수 있다.

| 항목 | 값 | 이유 |
|------|----|------|
| `staleTime` | 30초 | 같은 데이터를 짧은 시간 안에 다시 요청하지 않도록 한다 |
| `refetchOnWindowFocus` | `false` | 창을 오갈 때마다 불필요하게 다시 불러오지 않는다 |
| 쿼리 재시도 | 최대 2회, 4xx는 재시도 안 함 | 인증·검증 오류는 반복해도 결과가 같다 |
| 뮤테이션 재시도 | 안 함 | 생성·삭제 같은 쓰기 요청이 중복 실행되는 것을 막는다 |

비유하면 `queryClient`는 앱 전체가 함께 쓰는 "서버 응답 보관함"이고, `shouldRetry`는 "다시 시도해 볼 만한 실패인지" 판단하는 규칙이다.

## 변경 파일
- `frontend/src/lib/queryClient.ts` (신규): `queryClient`, `shouldRetry`
- `frontend/src/main.tsx`: `QueryClientProvider` 추가
- `frontend/tests/unit/queryClient.test.ts` (신규): 기본 옵션 및 재시도 정책 테스트 16개
- `frontend/src/App.tsx`: 동작 확인용 임시 `/query-test` 라우트와 import 제거
- `frontend/src/components/QueryTest.tsx`: 동작 확인용 임시 컴포넌트 삭제
- `specs/001-ai-code-learning-platform/tasks.md`: T019 완료 표시
- `docs/task-reports/TASK-019-TanStack-Query-클라이언트-설정.md` (신규): 작업 결과 기록

## TDD 결과
- RED 커밋: 해당 없음 (Git 저장소 아님). 구현 전 테스트가 `queryClient` 모듈 부재로 실패하는 것을 확인했다.
- GREEN 커밋: 해당 없음. 구현 후 테스트 16개 통과 (프론트엔드 전체 26개 통과).
- REFACTOR 커밋: 해당 없음. 별도 리팩터링 없음.
- 테스트 커버리지: `queryClient.ts` 100% (Stmts/Branch/Funcs/Lines). tsc, eslint, prettier 통과.

## 기술 결정
- **4xx 재시도 제외는 오류의 `response.status`로 판단**: T020의 axios 오류 형태와 맞춘다. 응답이 없는 네트워크 오류는 일시적일 수 있어 재시도한다.
- **`shouldRetry`를 별도 export**: 클라이언트 옵션 전체를 만들지 않고도 재시도 규칙만 단위 테스트할 수 있다.
- **`QueryClientProvider`는 `main.tsx`에 배치**: T018과 같은 방침이다. 테스트에서는 각자 새 `QueryClient`를 만들어 상태가 섞이지 않게 할 수 있다.

## 비고
- 사전에 TanStack Query 동작을 확인하려고 만든 임시 컴포넌트(`QueryTest`)와 `/query-test` 라우트는 이번 Task에서 제거했다. 그 확인은 JSONPlaceholder 더미 API 호출로 했다.
- `main.tsx`는 커버리지 대상에서 제외돼 있어, Provider 연결은 `tsc` 통과로만 확인했고 브라우저 화면에서 직접 확인하지는 않았다.
- Git 저장소가 아니라 커밋은 없다.
