# TASK-023. User SQLAlchemy 모델

## 상태
완료

## 날짜
2026-11-05

## 작업 요약
`users` 테이블에 대응하는 파이썬 클래스 `User`를 만들었다. 지금까지 DB 테이블은 마이그레이션(SQL)으로만 존재했는데, 이제 코드에서 `User(email=..., password_hash=...)`처럼 사용자를 다룰 수 있다.

비유하면 마이그레이션은 "건물 설계도 원본"이고, 모델은 "그 건물의 출입 안내판"이다. 안내판이 설계도와 다르면 사람들이 엉뚱한 문으로 들어가기 때문에, 이 모델은 설계도(T009 마이그레이션)와 글자 하나까지 맞추는 데 초점을 두었다.

| 컬럼 | 타입 | 규칙 |
|------|------|------|
| `id` | UUID | 기본키 (`UUIDPrimaryKeyMixin`) |
| `email` | VARCHAR(255) | 필수, 유일, 이메일 형식 검사(`valid_email`) |
| `password_hash` | VARCHAR(255) | 필수 (bcrypt 해시만 저장) |
| `skill_level` | VARCHAR(50) | 기본값 `'Complete Beginner'` |
| `created_at`, `updated_at` | 시간대 포함 시각 | `TimestampMixin` 재사용 |
| `last_login_at` | 시간대 포함 시각 | 비어 있을 수 있음 |

추가로 `email`에 `idx_users_email` 인덱스를 붙였다(로그인 조회용). `__repr__`은 `id`와 `email`만 보여 주고 `password_hash`는 뺐다. 로그에 객체가 찍혀도 해시가 새지 않게 하려는 것이다.

## 변경 파일
- `backend/src/models/user.py` (신규): `User` 모델
- `backend/src/models/__init__.py`: `User` 내보내기 (기존엔 빈 파일)
- `backend/tests/unit/test_user_model.py` (신규): 컬럼 목록·타입·길이·NULL 허용·유일성·기본값·인덱스·체크 제약 이름·생성·`repr` 테스트 12개
- `specs/001-ai-code-learning-platform/tasks.md`: T023 완료 표시
- `docs/task-reports/TASK-023-User-SQLAlchemy-모델.md` (신규): 작업 결과 기록

## TDD 결과
- RED 커밋: 해당 없음 (Git 저장소 아님). 구현 전 `from src.models import User`가 `ImportError`로 실패하는 것을 확인했다.
- GREEN 커밋: 해당 없음. 구현 후 12개 통과.
- REFACTOR 커밋: 해당 없음. 별도 리팩터링 대상 없음.
- 테스트 커버리지: 백엔드 전체 98% (`user.py` 100%, 남은 미커버는 DB 연결이 필요한 `db/session.py` 35-41행). 전체 180개 통과, 25개 스킵(PostgreSQL 필요). ruff, black, mypy(strict) 통과.

## 기술 결정
- **`valid_email` 이름 유지 (`conv` 사용)**: `base.py`의 이름 규칙은 체크 제약에 `ck_users_` 접두어를 붙인다. 그러면 마이그레이션의 `valid_email`과 이름이 달라져서, 나중에 Alembic이 두 이름을 서로 다른 제약으로 볼 수 있다. `conv()`로 규칙 적용을 막아 이름을 맞췄다.
- **관계(`relationship`)는 넣지 않음**: `refresh_tokens`, `projects` 관계는 상대 모델이 있어야 한다. T024(RefreshToken)가 [P]로 병렬 태스크이므로 T023은 단독으로 import되도록 두고, 관계는 T024 이후에 연결한다.
- **`skill_level`을 `str | None`으로 선언**: 마이그레이션이 이 컬럼에 NOT NULL을 걸지 않았기 때문이다. 기본값은 DB가 채운다.
- **`TimestampMixin` 재사용**: 이 믹스인은 `created_at`·`updated_at`을 NOT NULL로 선언한다. 마이그레이션은 두 컬럼에 DEFAULT만 있고 NOT NULL은 없다. 모델 쪽이 더 엄격하지만 DB 기본값이 항상 채우므로 동작에는 차이가 없어 그대로 썼다.

## 비고
- **DB 연동 검증은 하지 못했다.** Docker/PostgreSQL이 꺼져 있어(localhost:5432 접속 불가) 실제 `INSERT`·제약 위반 테스트는 돌리지 못했다. 모델 정의가 마이그레이션과 같은지는 메타데이터(컬럼·타입·제약·인덱스 이름) 수준에서만 확인했다. DB를 켠 뒤 T025(UserService)에서 통합 테스트로 확인하는 것이 좋다.
- **이메일 정규식 `[A-Z|a-z]`**: 마지막 글자 범위에 `|`가 들어 있어 `user@example.|m` 같은 값도 통과한다. data-model.md와 마이그레이션에서 온 오타로 보이며, 모델은 둘과 일치시키기 위해 그대로 옮겼다. 고치려면 마이그레이션도 함께 바꿔야 하므로 별도 태스크로 정하길 권한다. 서비스 레이어(T025)에서 이메일 검증을 한 번 더 하면 보완된다.
- **`idx_users_email`은 중복 인덱스**: `email`에 `UNIQUE`가 이미 있어 PostgreSQL이 인덱스를 자동으로 만든다. 마이그레이션이 같은 인덱스를 한 번 더 만들므로 모델도 이를 따랐다. 기능 문제는 없고 쓰기 시 약간의 낭비다.
- Git 저장소가 아니라 커밋은 없다.
