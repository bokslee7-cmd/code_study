# TASK-034. 인증 서비스 (auth-service)

## 상태
완료

## 날짜
2026-11-09

## 작업 요약
화면과 서버 사이의 "통역사 겸 우체부"를 만들었다. 화면은 `skillLevel`처럼 낙타 표기(camelCase)를 쓰고 서버는 `skill_level`처럼 뱀 표기(snake_case)를 쓰는데, 이 서비스가 편지를 주고받으면서 말투를 바꿔 준다. 그리고 쿠키가 필요한 편지에만 "쿠키 동봉(`withCredentials`)" 도장을 찍는다.

| 함수 | 호출 | 쿠키 동봉 | 돌려주는 값 |
|------|------|-----------|-------------|
| `register({email, password})` | `POST /auth/register` | 아니오 | `AuthUser` |
| `login({email, password})` | `POST /auth/login` | 예 | `{accessToken, expiresIn, user}` |
| `logout()` | `POST /auth/logout` | 예 | 없음 |
| `refresh()` | `POST /auth/refresh` | 예 | `{accessToken, expiresIn}` |
| `fetchMe(accessToken)` | `GET /auth/me` | 아니오 | `AuthUser` |

- 서버의 `skill_level`이 `null`이면 spec 기본값인 `"Complete Beginner"`로 채운다(`AuthUser.skillLevel`은 문자열 필수).
- 오류는 이미 api-client 인터셉터가 `ApiError`로 바꿔 주므로 서비스는 그대로 던진다. 자체 변환이나 삼키기가 없다.
- 이 서비스는 스토어를 건드리지 않는다. 세션 저장은 페이지/훅이 한다(순수하게 "요청 + 변환"만).

## 변경 파일
- `frontend/src/services/auth-service.ts` (신규)
- `frontend/tests/unit/auth-service.test.ts` (신규): 8개 케이스 (`apiClient.post/get`을 `vi.spyOn`으로 대체)

## TDD 결과
- RED 커밋: 해당 없음(Git 저장소 아님). 구현 전 `auth-service` 모듈이 없어 import 실패를 확인했다.
- GREEN 커밋: 해당 없음. 구현 후 8개 모두 통과.
- REFACTOR 커밋: 해당 없음. 변환 함수(`toAuthUser`, `toTokenResult`)를 작게 분리한 것으로 충분했다.
- 테스트 커버리지: `auth-service.ts` 100%.

## 기술 결정
- **`withCredentials`는 요청별로 지정**: api-client 전체에 켜면 모든 API 요청이 쿠키 모드가 되고, CORS 설정이 맞지 않는 다른 호출에도 영향을 준다. login/logout/refresh만 켠다. 기존 api-client 코드와 테스트는 건드리지 않았다.
- **`register`에는 쿠키를 붙이지 않음**: 계약상 응답에 토큰도 쿠키도 없다.
- **`fetchMe(accessToken)`가 토큰을 인자로 받음**: 세션 복구(T038) 순서가 `refresh -> me`인데, 그 시점에는 스토어에 사용자가 없다. 토큰을 먼저 스토어에 넣으면 "토큰은 있는데 사용자는 없는" 어중간한 상태가 잠깐 생긴다. 방금 받은 토큰을 헤더에 직접 실어 보내고, 성공하면 토큰과 사용자를 한 번에 저장하게 했다.
- **`logout()`이 바디 없이 `undefined`를 보냄**: 계약이 "바디 없음"이라서 그대로 맞췄다.

## 비고
- 브라우저가 크로스 오리진(`localhost:5173` -> `localhost:8000`)으로 쿠키를 주고받으려면 백엔드가 `Access-Control-Allow-Credentials: true`와 구체적인 `allow_origins`(와일드카드 `*` 불가)를 내려줘야 한다. 이는 백엔드 CORS 설정 확인 요청 사항으로 최종 보고에 적었다.
- Git 저장소가 아니라 커밋은 없다.
