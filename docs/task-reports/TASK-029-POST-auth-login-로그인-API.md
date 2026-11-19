# TASK-029. POST /auth/login (로그인 API)

## 상태
완료

## 날짜
2026-11-09

## 작업 요약
로그인 창구를 열었다. 손님이 이메일과 비밀번호를 내면 신원 확인 담당(`UserService.login`)이 맞는지 확인하고, 맞으면 발급 담당(`TokenService.create_tokens`)이 두 가지 입장권을 만든다. 하루짜리 일일 이용권(액세스 토큰)은 손에 쥐여 주는 응답 본문에 담고, 오래 쓰는 정기권(리프레시 토큰)은 손님의 지갑 속 잠금 주머니(HttpOnly 쿠키)에 직접 넣어 준다. 정기권은 자바스크립트가 읽을 수 없는 쿠키에만 들어가고 본문에는 나오지 않는다.

| 항목 | 값 |
|------|-----|
| 상태 코드 | 200 |
| 본문 | `{"access_token", "token_type": "bearer", "expires_in": <초>, "user": {...}}` |
| 쿠키 | `refresh_token=<토큰>; HttpOnly; SameSite=Strict; Path=/api/v1/auth; Max-Age=<7일(초)>`, `Secure`는 `COOKIE_SECURE` 설정값 |
| 자격 증명 오류 | 401 (쿠키 없음) |
| 필드 누락 | 400 `validation_error` |

## 변경 파일
- `backend/src/api/auth.py`: `login` 라우트
- `backend/src/api/auth_cookies.py` (신규): 쿠키 이름/경로, `set_refresh_cookie`, `delete_refresh_cookie`, `cookie_secure`, `token_lifetime_seconds`
- `backend/src/api/schemas/auth.py`: `TokenResponse`, `LoginResponse`
- `.env.example`: `COOKIE_SECURE=false` 항목 추가
- `backend/tests/unit/test_auth_api.py`: 로그인 9개 + 쿠키 설정값 14개 케이스
- `docs/task-reports/TASK-029-POST-auth-login-로그인-API.md` (신규): 이 보고서

## TDD 결과
- RED 커밋: 해당 없음 (Git 저장소 아님). 구현 전 `tests/unit/test_auth_api.py`가 `src.api.auth_cookies` 모듈이 없어 `ImportError`(수집 단계 실패)로 멈추는 것을 확인했다.
- GREEN 커밋: 해당 없음. 구현 후 `test_auth_api.py` 50개 통과.
- REFACTOR 커밋: 해당 없음. 쿠키 속성을 한 곳(`auth_cookies.py`)에 모아 로그인, 갱신, 로그아웃이 같은 속성을 쓰게 했다.
- 테스트 커버리지: 신규 코드(`auth.py`, `auth_cookies.py`, `schemas/auth.py`, `dependencies.py`) 100%. 백엔드 전체 314개 통과, 25개 스킵(Docker/DB가 꺼져 있어 DB 통합 테스트가 스킵됨), ruff, black, mypy(strict) 통과.

## 기술 결정
- **`expires_in`과 쿠키 `Max-Age`를 토큰 자체에서 계산**: 토큰의 `exp - iat`를 읽는다. `JWT_ACCESS_TOKEN_MINUTES`, `JWT_REFRESH_TOKEN_DAYS` 설정을 응답 쪽에서 따로 읽으면 두 군데가 어긋날 수 있는데, 토큰에서 읽으면 항상 실제 수명과 같다(설정을 바꿔도 테스트로 일치 확인).
- **`Secure` 플래그는 `COOKIE_SECURE` 환경변수**: 기본 false(로컬 http 개발), 운영에서 true. `true/false/1/0/yes/no/on/off`와 빈 값만 허용하고 그 밖의 값은 `ValueError`를 낸다. `db/config.py`의 불리언 파싱과 같은 규칙이다. 설정은 요청 시점에 읽는다.
- **쿠키 `Path=/api/v1/auth`**: 정기권은 인증 API로만 전송되고 다른 API 요청에는 따라가지 않는다.
- **`SameSite=Strict`**: 계약대로. CSRF 토큰(T199)과 쿠키 보안 강화(T201)는 범위 밖이다.
- **자격 증명 오류 시 쿠키/토큰 미발급**: 신원 확인에서 예외가 나면 `create_tokens`는 호출되지 않는다(테스트로 확인).

## 비고
- 속도 제한(T192)은 범위 밖이다.
- 실제 PostgreSQL이 꺼져 있어 실제 DB 대상 확인은 하지 못했다.
- CORS(`allow_credentials=True`, 와일드카드 금지, 명시 origin 목록)는 이미 `main.py`에 구현되어 있고 `test_main.py`가 검증한다. 로그인 경로에 대한 프리플라이트 테스트를 하나 추가해 확인했다. 코드 수정은 없었다.
- Git 저장소가 아니라 커밋은 없다.
