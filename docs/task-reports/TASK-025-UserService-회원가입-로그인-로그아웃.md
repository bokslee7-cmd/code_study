# TASK-025. UserService (회원가입·로그인·로그아웃)

## 상태
완료

## 날짜
2026-11-05

## 작업 요약
회원가입, 로그인, 로그아웃의 "업무 규칙"을 담당하는 `UserService`를 만들었다. 모델(T023·T024)이 "장부의 칸"이라면, 서비스는 "접수 창구 직원"이다. 직원은 서류가 맞는지 보고(검증), 이미 가입했는지 장부에서 찾아 보고(중복 확인), 장부에 적는(저장) 일을 한다. 화면이나 HTTP 요청은 모르고, 세션만 받아서 일한다(헌법 III: API → Service → Model).

| 기능 | 하는 일 | 실패 시 |
|------|---------|---------|
| `register(email, password)` | 이메일을 소문자·공백 제거로 정리 → 이메일·비밀번호 형식 확인 → 중복 확인 → 비밀번호를 bcrypt로 해시해 저장 | 형식 오류 400, 중복 409 |
| `login(email, password)` | 이메일로 사용자 찾기 → 비밀번호 확인 → 마지막 로그인 시각 기록 → 약한 해시면 새 해시로 교체 | 401 (이메일 없음/비밀번호 틀림 구분 안 함) |
| `logout(refresh_token)` | 받은 리프레시 토큰의 지문(SHA-256)으로 DB 행을 찾아 폐기 표시(`revoked`, `revoked_at`) | 없거나 이미 폐기됐어도 오류 아님 |

로그인과 로그아웃을 이렇게 나눈 이유는 토큰 발급이 T026(TokenService)의 일이기 때문이다. `login`은 "누구인지 확인된 사용자"만 돌려주고, 토큰은 API 계층(T029)이 서비스 둘을 이어서 만든다.

## 변경 파일
- `backend/src/services/auth/user_service.py` (신규): `UserService`, `normalize_email`
- `backend/src/services/__init__.py`, `backend/src/services/auth/__init__.py` (신규, 빈 파일): 패키지로 인식시키기 위함
- `backend/src/api/exceptions.py`: `UnauthorizedException`(401) 추가. 기존 `NotFound/Forbidden/Conflict`와 같은 형태이며 T027·T029~T031에서도 쓴다.
- `backend/tests/unit/test_user_service.py` (신규): 회원가입 16개 케이스(잘못된 이메일 8종·약한 비밀번호 3종 포함), 로그인 7개, 로그아웃 3개, 합계 26개
- `backend/tests/unit/test_unauthorized_exception.py` (신규): 새 예외 2개. 기존 `test_test_errors.py`는 수정하지 않았다.
- `specs/001-ai-code-learning-platform/tasks.md`: T025 완료 표시
- `docs/task-reports/TASK-025-UserService-회원가입-로그인-로그아웃.md` (신규): 작업 결과 기록

## TDD 결과
- RED 커밋: 해당 없음 (Git 저장소 아님). 구현 전 `UnauthorizedException`과 `user_service`가 없어 두 테스트 파일이 `ImportError`로 실패하는 것을 확인했다.
- GREEN 커밋: 해당 없음. 구현 후 28개 통과.
- REFACTOR 커밋: 해당 없음. black·ruff 지적(비밀번호 안내 문구 한 줄 길이)을 상수 분리로 정리했다.
- 테스트 커버리지: 백엔드 전체 98% (`user_service.py` 100%, `exceptions.py` 100%). 전체 221개 통과, 25개 스킵(PostgreSQL 필요). ruff, black, mypy(strict) 통과.

## 기술 결정
- **로그인 실패 메시지를 하나로 통일**: "이메일 또는 비밀번호가 올바르지 않습니다." 하나만 쓴다. 어느 쪽이 틀렸는지 알려 주면 공격자가 가입된 이메일 목록을 알아낼 수 있다.
- **없는 이메일에도 bcrypt 검사를 한 번 수행**: 이메일이 없다고 바로 실패시키면 응답이 빨라서 "없는 이메일"임이 시간 차이로 드러난다. 미리 만든 가짜 해시로 같은 검사를 하게 해 걸리는 시간을 맞췄다(가짜 해시는 처음 필요할 때 한 번만 만든다).
- **서비스는 `flush`만, `commit`은 하지 않음**: 요청 단위 세션(`get_session`)이 성공하면 커밋, 실패하면 롤백한다. 서비스가 커밋하면 한 요청 안에서 여러 서비스를 묶어 롤백할 수 없다.
- **저장·로그인 뒤 `session.refresh(user)`**: 비동기 세션에서는 DB가 채운 값(`created_at`, 갱신된 `updated_at`)을 나중에 읽으면 오류(`MissingGreenlet`)가 난다. API 응답에서 안전하게 쓰도록 미리 불러온다. 쿼리 1회가 늘어나는 대신 함정을 없앴다.
- **이메일 검증을 서비스에서 한 번 더**: DB 규칙의 정규식에는 `[A-Z|a-z]`처럼 `|`가 끼어 있어(TASK-023 비고) `a@b.|m` 같은 값이 통과한다. 서비스는 `[A-Za-z]`로 바로잡은 규칙을 쓴다. DB 규칙보다 엄격한 부분집합이라 서비스를 통과한 값은 DB도 항상 통과한다. 길이는 255자까지다.
- **동시 가입 경쟁 처리**: 중복 확인과 저장 사이에 같은 이메일이 들어오면 DB의 UNIQUE가 `IntegrityError`를 내므로 이를 잡아 409로 바꾼다.
- **비밀번호 오류 메시지는 한국어 고정 문구**: `security.py`의 영어 `ValueError` 메시지를 그대로 노출하지 않고, 입력한 비밀번호도 메시지에 담지 않는다(테스트로 확인).
- **로그아웃은 토큰 하나만 폐기, 멱등**: 없는 토큰이나 이미 폐기된 토큰도 성공으로 본다. 이미 폐기된 행의 `revoked_at`은 덮어쓰지 않아 최초 폐기 시각이 남는다. 로그아웃 시점엔 액세스 토큰이 이미 만료됐을 수 있어 사용자 인증 없이 리프레시 토큰만으로 동작하게 했다.
- **새 `AppError` 하위 클래스를 만들지 않음**: 형식 오류는 기존 `AppError`에 `VALIDATION_ERROR` 코드와 `details={"field": ...}`를 실어 400으로 낸다. 프런트엔드가 어느 입력칸에 오류를 표시할지 `details.field`로 알 수 있다.

## 비고
- **DB 연동 검증은 하지 못했다.** Docker/PostgreSQL이 꺼져 있고(localhost:5432 접속 불가) 로컬 설치나 `aiosqlite`도 없다. 그래서 테스트는 세션을 대역(mock)으로 바꿔서 "어떤 순서로 무엇을 호출하는가"와 "조회 SQL에 소문자 이메일·토큰 지문이 들어가는가"를 확인한다. 아래는 실제 DB가 있어야 확인되는 항목이다.
  - 실제 `UNIQUE` 위반이 `IntegrityError`로 올라와 409로 바뀌는지
  - `refresh()`로 `created_at`·`updated_at`이 실제로 채워지는지
  - 로그아웃이 실제 행의 `revoked`를 바꾸는지
  Docker를 켠 뒤 통합 테스트(`test_initial_migration.py` 방식)로 추가하길 권한다. 기기 상태를 바꾸는 Docker 기동은 임의로 하지 않았다.
- **비밀번호 정책은 길이만 본다**: 8자 이상, 72바이트 이하(기존 `security.py` 규칙)다. 대소문자·숫자 조합 같은 복잡도 규칙은 스펙에 없어 넣지 않았다.
- **이메일 중복 가입 응답(409)은 가입 여부를 드러낸다.** 회원가입의 일반적인 특성이며, 남용은 요구사항 보충(CHK049)의 속도 제한(IP당 시간당 3계정 등)으로 막는 것이 계획이다. 속도 제한은 이 태스크 범위가 아니다.
- **계정 잠금(로그인 실패 횟수 제한)은 구현하지 않았다.** 속도 제한(IP당 15분 5회)과 함께 별도 태스크에서 다룬다.
- 다음 태스크 T026(TokenService)이 리프레시 토큰 행을 만들 때 `token_hash`는 `src.utils.jwt.hash_token`을 쓴다. `logout`이 같은 함수로 조회하므로 두 쪽이 반드시 같은 해시 함수를 써야 한다.
- Git 저장소가 아니라 커밋은 없다.
