# TASK-020. API 클라이언트 기반 (axios 설정)

## 상태
완료

## 날짜
2026-11-03

## 작업 요약
`frontend/src/services/api-client.ts`에 모든 API 호출이 공통으로 쓸 axios 인스턴스(`apiClient`)를 만들었다. 이후 서비스 파일(프로젝트, 태스크 등)은 이 인스턴스로 요청만 보내면 된다.

| 구성 | 내용 |
|------|------|
| 기본 주소 | `VITE_API_BASE_URL`, 비어 있으면 `http://localhost:8000/api/v1` |
| 타임아웃 | 10초 |
| 인증 헤더 | 토큰 공급자가 토큰을 주면 `Authorization: Bearer <토큰>`을 자동으로 붙임 |
| 오류 변환 | 모든 실패를 `ApiError`로 통일 |

`ApiError`는 백엔드 `ErrorResponse`(`error`, `message`, `details`, `suggestion`)를 `code`, `message`, `details`, `suggestion`, `status`로 옮긴 오류다. 서버에 닿지 못하면 `network_error`, 시간이 초과되면 `timeout`, 형식을 알 수 없는 응답(예: 프록시의 HTML 오류 페이지)은 `unknown_error`로 바뀌고, 이 경우 화면에는 안내 문구만 보인다.

비유하면 `apiClient`는 모든 화면이 함께 쓰는 "공용 우체국 창구"다. 보낼 때 신분증(토큰)을 자동으로 붙이고, 돌아온 반송 사유는 항상 같은 양식(`ApiError`)으로 바꿔 준다.

## 변경 파일
- `frontend/src/services/api-client.ts` (신규): `apiClient`, `ApiError`, `toApiError`, `setAuthTokenProvider`
- `frontend/src/vite-env.d.ts`: `VITE_API_BASE_URL`, `VITE_ENVIRONMENT` 타입 선언
- `frontend/tests/unit/api-client.test.ts` (신규): 기본 설정, 인증 헤더, 오류 변환, 재시도 정책 연동 테스트 18개
- `specs/001-ai-code-learning-platform/tasks.md`: T020 완료 표시
- `docs/task-reports/TASK-020-API-클라이언트-기반-axios-설정.md` (신규): 작업 결과 기록

## TDD 결과
- RED 커밋: 해당 없음 (Git 저장소 아님). 구현 전 테스트가 `api-client` 모듈 부재로 실패하는 것을 확인했다.
- GREEN 커밋: 해당 없음. 구현 후 18개 통과 (프론트엔드 전체 44개 통과).
- REFACTOR 커밋: 해당 없음. 미커버 분기(응답 없는 기타 axios 오류) 테스트를 추가하고 Prettier 포맷을 맞췄다.
- 테스트 커버리지: `api-client.ts` 100% (Stmts/Branch/Funcs/Lines), 전체 100%. tsc, eslint, prettier 통과.

## 기술 결정
- **토큰은 `setAuthTokenProvider`로 주입**: JWT 상태 저장소(T021 auth-store)가 아직 없고, 나중에 store가 api-client를 import하면 서로를 불러 순환 의존이 생길 수 있다. T021에서 `setAuthTokenProvider(() => useAuthStore.getState().accessToken)` 형태로 등록하면 된다.
- **`ApiError.response.status`를 노출**: T019의 `shouldRetry`가 `error.response.status`로 4xx를 판단한다. 같은 모양을 제공해 `queryClient.ts`를 고치지 않고도 4xx는 재시도하지 않고, 5xx와 네트워크 오류는 재시도하도록 맞췄다. 테스트로 연동을 검증했다.
- **취소된 요청은 변환하지 않음**: TanStack Query가 요청을 취소할 때(`AbortController`)는 오류가 아니므로 `axios.isCancel`로 구분할 수 있게 그대로 던진다.
- **타임아웃 10초**: 문서·연습 문제 생성은 Celery 비동기로 처리되므로 API 호출 자체는 짧게 끝난다는 전제다. 파일 업로드처럼 오래 걸릴 수 있는 요청은 호출 시 `timeout`을 따로 지정한다.

## 비고
- 401 응답 시 토큰 자동 갱신과 로그인 화면 이동은 포함하지 않았다. T038(`useAuth` 자동 갱신)의 범위다. 이때 응답 인터셉터에서 `ApiError.status === 401`을 확인하면 된다.
- 실제 백엔드 서버에 요청을 보내 확인하지는 않았다. axios 어댑터를 대체해 요청 설정과 응답·오류 변환만 단위 테스트로 검증했다.
- Git 저장소가 아니라 커밋은 없다.
