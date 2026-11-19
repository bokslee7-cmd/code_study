# TASK-012. JWT 토큰 유틸리티

## 상태
완료

## 날짜
2026-10-30

## 작업 요약
`backend/src/utils/jwt.py`를 구현했다 (python-jose, HS256).
- `create_access_token(subject, expires_delta=None, extra_claims=None)`: 기본 15분 (`JWT_ACCESS_TOKEN_MINUTES`)
- `create_refresh_token(...)`: 기본 7일 (`JWT_REFRESH_TOKEN_DAYS`). research.md의 인증 정책과 같다.
- `decode_token(token)`: 서명·만료 검증 후 claims 반환. 만료는 `TokenExpiredError`, 그 외(변조, 다른 키, 다른 알고리즘, `alg=none`, 필수 claim 누락, 형식 오류)는 `InvalidTokenError`. 둘 다 `TokenError`의 하위 클래스.
- `verify_token(token, expected_type)`: `decode_token` + 토큰 종류(access/refresh) 확인. refresh 토큰을 access로 쓰는 것을 막는다.
- `hash_token(token)`: SHA-256 hex. data-model.md의 `refresh_tokens.token_hash` 저장용.
- 모든 토큰에 `sub`, `type`, `iat`, `exp`, `jti`(UUID)가 들어간다. `jti` 덕분에 같은 초에 발급해도 토큰이 서로 다르다(refresh 토큰 회전에 필요).
- `JWT_SECRET_KEY`는 필수이며 32자 미만이면 `RuntimeError`.

## 변경 파일
- backend/src/utils/__init__.py (신규, 빈 파일)
- backend/src/utils/jwt.py (신규)
- backend/tests/unit/test_jwt.py (신규, 25개)
- backend/requirements.txt (수정: `types-python-jose` 추가, mypy strict용 타입 스텁)
- .env.example (수정: `JWT_SECRET_KEY`, `JWT_ACCESS_TOKEN_MINUTES`, `JWT_REFRESH_TOKEN_DAYS`)
- specs/001-ai-code-learning-platform/tasks.md (T012 체크)

## TDD 결과
- RED 커밋: 해당 없음 (Git 저장소 아님). `src.utils.jwt`가 없어 수집 단계 ImportError 확인.
- GREEN 커밋: 해당 없음. 구현 후 jwt 테스트 25개 통과, 백엔드 전체 83개 통과 / 25개 skip.
- REFACTOR 커밋: 해당 없음. ruff·black·mypy 통과.
- 테스트 커버리지: `src/utils/jwt.py` 100%

skip 25개는 PostgreSQL(localhost:5432)이 필요한 기존 통합 테스트이며, Docker가 꺼져 있어 TASK-011과 마찬가지로 이번에도 실행하지 못했다. JWT 코드는 DB를 쓰지 않아 영향이 없다.

## 기술 결정
- **알고리즘은 HS256 하나로 고정하고 `decode`에서 `algorithms=[ALGORITHM]`만 허용**: 토큰 헤더의 `alg`를 믿지 않는다. 다른 알고리즘과 `alg=none` 토큰은 테스트로 거부를 확인했다.
- **`extra_claims`가 예약 claim(`sub`, `type`, `exp`, `iat`, `jti`)을 덮어쓰지 못함**: 호출자 실수로 만료·종류가 바뀌는 것을 막는다.
- **비밀키는 환경변수 필수, 기본값 없음**: 코드에 기본 시크릿을 두면 운영에 그대로 배포될 위험이 있다. 길이 검사로 약한 키도 막는다.
- **만료 시간 설정이 잘못되면 `ValueError`**: TASK-011과 같은 방식(조용히 기본값으로 대체하지 않음).
- **`types-python-jose` 추가**: mypy strict에서 jose에 타입 정보가 없어 필요하다.

## 비고
- python-jose 3.3.0이 내부에서 `datetime.utcnow()`를 써서 Python 3.12에서 DeprecationWarning이 14건 나온다. 라이브러리 내부 문제이며 동작에는 영향이 없다. 라이브러리 유지보수가 거의 멈춘 상태라, 이후 PyJWT 전환을 검토할 만하다(이번 범위에서는 plan/requirements의 지정을 따랐다).
- 토큰 쿠키 설정(HTTPOnly, Secure), refresh 토큰 DB 저장·회전·폐기는 인증 서비스 태스크(US1)에서 다룬다. 이 모듈은 토큰 생성·검증만 담당한다.
- Git 저장소가 아니라 커밋은 없다.
- 다음 작업: T013 (비밀번호 해싱).
