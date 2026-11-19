# TASK-031. POST /auth/refresh (토큰 갱신 API)

## 상태
완료

## 날짜
2026-11-09

## 작업 요약
이용권 재발급 창구를 열었다. 일일 이용권이 만료됐을 때 손님이 정기권(리프레시 토큰 쿠키)을 내밀면 직원이 `TokenService.rotate`로 옛 정기권을 폐기하고 새 일일 이용권과 새 정기권을 한 쌍으로 발급한다. 새 일일 이용권은 본문에, 새 정기권은 다시 같은 속성의 쿠키로 내려간다. 정기권이 없거나 가짜이거나 만료, 폐기됐으면 401을 주면서, 손님 주머니에 남은 낡은 쿠키도 같이 치워 준다.

| 상황 | 결과 |
|------|------|
| 유효한 쿠키 | 200 `{"access_token", "token_type": "bearer", "expires_in"}` + 새 refresh_token 쿠키 |
| 쿠키 없음/빈 값 | 401 + 쿠키 삭제 헤더 (서비스 호출 없음) |
| 무효/만료/폐기된 토큰 | 401 + 쿠키 삭제 헤더 |

## 변경 파일
- `backend/src/api/auth.py`: `refresh` 라우트와 `_reject_refresh` 헬퍼
- `backend/tests/unit/test_auth_api.py`: 갱신 6개 케이스
- `docs/task-reports/TASK-031-POST-auth-refresh-토큰-갱신-API.md` (신규): 이 보고서

## TDD 결과
- RED 커밋: 해당 없음 (Git 저장소 아님). 구현 전 `tests/unit/test_auth_api.py`가 `src.api.auth_cookies` 모듈이 없어 `ImportError`(수집 단계 실패)로 멈추는 것을 확인했다.
- GREEN 커밋: 해당 없음. 구현 후 `test_auth_api.py` 50개 통과.
- REFACTOR 커밋: 해당 없음. `refresh`에서 try 안에서 raise 후 바로 catch하던 흐름을 `_reject_refresh` 헬퍼와 early return으로 풀어 읽기 쉽게 했다. 테스트는 그대로 통과했다.
- 테스트 커버리지: 신규 코드(`auth.py`, `auth_cookies.py`, `schemas/auth.py`, `dependencies.py`) 100%. 백엔드 전체 314개 통과, 25개 스킵(Docker/DB가 꺼져 있어 DB 통합 테스트가 스킵됨), ruff, black, mypy(strict) 통과.

## 기술 결정
- **오류 응답에 쿠키 삭제를 붙이기 위해 예외를 라우트에서 직접 받음**: 일반 예외 핸들러가 만드는 응답에는 라우트가 쿠키 헤더를 얹을 수 없다. 그래서 `UnauthorizedException`을 잡아 기존 `app_error_handler`로 똑같은 형식(`error`, `message`)의 응답을 만들고 그 위에 삭제 헤더를 붙였다. 오류 본문 형식은 다른 API와 동일하다.
- **응답에 사용자 객체 없음**: 계약대로 `{access_token, token_type, expires_in}`만 준다. 사용자 정보는 필요하면 `/me`로 얻는다.
- **회전(rotate)은 서비스에 위임**: 행 잠금으로 같은 토큰의 동시 요청이 둘 다 성공하지 못하게 하는 것은 T026의 `TokenService.rotate`가 이미 보장한다. 라우트는 호출만 한다.
- **실패 경로에서 DB 쓰기 없음**: `rotate`는 검증이 실패하면 아무것도 쓰기 전에 예외를 내므로, 예외를 삼켜 응답으로 바꿔도 부분 변경이 남지 않는다.

## 비고
- 속도 제한(`/auth/refresh` 분당 10회 등, T192)은 범위 밖이다.
- 이미 폐기된 토큰이 재사용될 때 해당 사용자의 모든 토큰을 폐기하는 "재사용 탐지"는 요구되지 않아 구현하지 않았다.
- Git 저장소가 아니라 커밋은 없다.
