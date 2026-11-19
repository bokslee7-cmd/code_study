# TASK-013. 비밀번호 해싱 유틸리티

## 상태
완료

## 날짜
2026-10-30

## 작업 요약
`backend/src/utils/security.py`를 구현했다 (passlib + bcrypt, cost factor 12 — research.md, data-model.md 기준).
- `hash_password(password)`: bcrypt 해시 생성(`$2b$12$...`, 60자라 `password_hash VARCHAR(255)`에 들어감). 빈 문자열과 72바이트 초과는 `ValueError`.
- `verify_password(password, password_hash)`: 일치하면 True. 불일치, 72바이트 초과 입력, 형식이 깨진 해시는 예외 없이 False.
- `needs_rehash(password_hash)`: 비용이 낮은 옛 해시인지 확인. 로그인 성공 시 해시를 업그레이드할 때 쓴다.
- `validate_password(password)`: 길이 정책(최소 8자, 최대 72바이트). 위반하면 `ValueError`. research.md의 "min 8 chars"를 반영.

## 변경 파일
- backend/src/utils/security.py (신규)
- backend/tests/unit/test_security.py (신규, 16개)
- backend/requirements.txt (수정: mypy strict용 `types-passlib` 추가)
- specs/001-ai-code-learning-platform/tasks.md (T013 체크)

## TDD 결과
- RED 커밋: 해당 없음 (Git 저장소 아님). `src.utils.security`가 없어 수집 단계 오류 확인.
- GREEN 커밋: 해당 없음. 구현 후 security 테스트 16개 통과, 백엔드 전체 99개 통과 / 25개 skip.
- REFACTOR 커밋: 해당 없음. ruff·black·mypy 통과.
- 테스트 커버리지: `src/utils/security.py` 100%

skip 25개는 PostgreSQL이 필요한 기존 통합 테스트로, Docker가 꺼져 있어 이번에도 실행하지 못했다. 이 모듈은 DB를 쓰지 않는다.

## 기술 결정
- **72바이트 초과 비밀번호는 잘라내지 않고 거부**: bcrypt는 72바이트 뒤를 무시하므로, 그대로 두면 앞부분이 같은 서로 다른 비밀번호가 같은 해시로 통과한다. 한글은 글자당 3바이트라 글자 수가 아니라 바이트로 센다.
- **`verify_password`는 예외 대신 False**: 깨진 해시나 이상한 입력이 500 오류가 아니라 로그인 실패로 처리되게 한다.
- **복잡도 규칙(대소문자·숫자 조합)은 넣지 않음**: research.md에 "complexity rules"가 언급만 있고 구체 규칙이 없다. 정해지면 `validate_password`에 추가한다.
- **정책 검증(`validate_password`)과 해싱을 분리**: 관리자가 임시 비밀번호를 DB에 직접 넣는 경우 등 해싱 자체는 정책과 무관하게 동작해야 하고, 가입·비밀번호 변경 API에서 `validate_password`를 호출하면 된다.
- **`types-passlib` 추가**: mypy strict에서 passlib 타입 정보가 없어 필요하다.
- **시간 정보 노출 방지는 이번 범위 밖**: 존재하지 않는 사용자 로그인 시 해시 비교를 생략하면 응답 시간 차이로 계정 존재가 드러날 수 있다. 인증 서비스(US1)에서 더미 해시 비교로 처리한다.

## 비고
- `requirements.txt`가 `bcrypt==4.0.1`로 고정돼 있는 이유(passlib 1.7.4가 bcrypt 4.1 이상과 호환되지 않음)가 이 모듈에도 그대로 적용된다. bcrypt 버전을 올릴 때는 이 테스트를 먼저 돌려 확인해야 한다.
- cost 12 해시는 한 번에 약 0.2~0.3초 걸려 테스트 시간이 조금 늘어난다.
- Git 저장소가 아니라 커밋은 없다.
- 다음 작업: T014 (FastAPI 앱 초기화).
