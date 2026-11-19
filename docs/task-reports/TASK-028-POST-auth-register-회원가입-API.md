# TASK-028. POST /auth/register (회원가입 API)

## 상태
완료

## 날짜
2026-11-09

## 작업 요약
가입 창구를 열었다. 손님이 이메일과 비밀번호를 적어 내면 창구 직원(라우트)은 서류 심사를 직접 하지 않고, 뒤에 있는 심사 담당(`UserService.register`)에게 그대로 넘긴다. 심사 담당이 형식 검사, 중복 검사, 비밀번호 해시 저장을 마치면 직원은 "가입 완료" 영수증만 건넨다. 영수증에는 회원 정보(`id`, `email`, `skill_level`)만 적히고, 입장권(토큰)이나 쿠키는 주지 않는다. 가입 후 로그인은 별도 창구(T029)에서 한다.

| 상황 | 결과 |
|------|------|
| 정상 가입 | 201 `{"user": {"id", "email", "skill_level"}}`, 쿠키/토큰 없음 |
| 이미 가입된 이메일 | 409 (서비스가 발생시킨 `ConflictException` 그대로) |
| 이메일 형식/비밀번호 규칙 위반 | 400 (서비스가 발생시킨 검증 오류 그대로) |
| 필드 누락, 타입 오류 | 400 `validation_error` (Pydantic 스키마 검증) |

## 변경 파일
- `backend/src/api/auth.py` (신규): `register` 라우트 (인증 라우터 `/auth`)
- `backend/src/api/schemas/__init__.py`, `backend/src/api/schemas/auth.py` (신규): `Credentials`, `UserResponse`, `RegisterResponse` 등 요청/응답 스키마
- `backend/src/api/dependencies.py`: `get_user_service`, `get_token_service` 추가 (서비스를 요청 세션에 묶는 의존성)
- `backend/src/api/router.py`: `create_api_router`에 `auth.router` 포함 (`/api/v1/auth/...`)
- `backend/tests/unit/test_auth_api.py` (신규): T028~T031 공용 50개 케이스 중 가입 관련 8개 + 라우트 연결 3개
- `docs/task-reports/TASK-028-POST-auth-register-회원가입-API.md` (신규): 이 보고서

## TDD 결과
- RED 커밋: 해당 없음 (Git 저장소 아님). 구현 전 `tests/unit/test_auth_api.py`가 `src.api.auth_cookies` 모듈이 없어 `ImportError`(수집 단계 실패)로 멈추는 것을 확인했다.
- GREEN 커밋: 해당 없음. 구현 후 `test_auth_api.py` 50개 통과.
- REFACTOR 커밋: 해당 없음. 고칠 부분이 없었다.
- 테스트 커버리지: 신규 코드(`auth.py`, `auth_cookies.py`, `schemas/auth.py`, `dependencies.py`) 100%. 백엔드 전체 314개 통과, 25개 스킵(Docker/DB가 꺼져 있어 DB 통합 테스트가 스킵됨), ruff, black, mypy(strict) 통과.

## 기술 결정
- **서비스 더블로 HTTP 계약만 검증**: 라우트 테스트에서 `UserService`/`TokenService`를 가짜로 바꾸고 `get_session`도 가짜 세션으로 바꿨다. 심사 규칙은 이미 `test_user_service.py`가 검증하므로, 여기서는 "상태 코드, 응답 모양, 서비스 호출 인자"라는 창구의 약속만 확인한다.
- **요청 스키마는 `str`만**: 이메일 형식과 비밀번호 규칙은 `UserService`가 한 곳에서 판단한다(헌법 X-11, 비즈니스 로직은 서비스에). 스키마까지 같은 규칙을 갖게 하면 규칙이 두 곳에 생겨 어긋날 수 있다.
- **응답에 비밀번호 관련 필드 없음**: `UserResponse`가 필드를 명시적으로 3개만 가지므로 `password_hash`가 실수로 새지 않는다(테스트로 확인).
- **서비스 의존성을 `dependencies.py`에 둠**: 라우트가 `AsyncSession`을 직접 만지지 않고(X-12) 서비스만 받는다. 테스트에서 `dependency_overrides`로 갈아 끼우기도 쉽다.

## 비고
- 실제 PostgreSQL이 꺼져 있어(Docker 미실행) 실제 DB 대상 end-to-end 확인은 하지 못했다. 서비스 단위 테스트와 라우트 테스트는 각각 통과한다.
- Git 저장소가 아니라 커밋은 없다.
