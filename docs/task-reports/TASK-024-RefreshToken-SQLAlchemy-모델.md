# TASK-024. RefreshToken SQLAlchemy 모델

## 상태
완료

## 날짜
2026-11-05

## 작업 요약
`refresh_tokens` 테이블에 대응하는 파이썬 클래스 `RefreshToken`을 만들고, T023에서 미뤄 둔 `User`와의 연결(관계)도 이어 붙였다.

리프레시 토큰은 "놀이공원 자유이용권을 다시 발급받는 교환권"과 비슷하다. 로그인 상태를 오래 유지하려면 서버가 "이 교환권이 누구 것이고, 언제까지 유효하며, 이미 쓴 것인지"를 기억해야 하는데, 그 기록 한 줄이 이 모델의 한 행이다. 교환권 원본은 저장하지 않고 SHA-256 지문(`token_hash`)만 저장한다. DB가 유출돼도 지문만으로는 교환권을 다시 만들 수 없게 하려는 것이다.

| 컬럼 | 타입 | 규칙 |
|------|------|------|
| `id` | UUID | 기본키 (`UUIDPrimaryKeyMixin`) |
| `user_id` | UUID | 필수, `users.id` 외래키, 사용자 삭제 시 함께 삭제(`CASCADE`) |
| `token_hash` | VARCHAR(255) | 필수, 유일 |
| `expires_at` | 시간대 포함 시각 | 필수 (생성 후 7일) |
| `created_at` | 시간대 포함 시각 | 서버 기본값 `now()` |
| `revoked` | BOOLEAN | 기본값 `false` (DB와 파이썬 양쪽) |
| `revoked_at` | 시간대 포함 시각 | 비어 있을 수 있음 |

인덱스는 마이그레이션과 같은 이름으로 3개(`idx_refresh_tokens_user_id`, `_hash`, `_expires`)를 붙였다.

관계는 `User.refresh_tokens`(한 사용자가 여러 토큰)와 `RefreshToken.user`(토큰의 주인) 양방향이다. `User` 쪽에는 `passive_deletes=True`를 걸었다. 사용자를 지울 때 파이썬이 토큰을 하나씩 불러 지우지 않고, DB의 `ON DELETE CASCADE`에 맡기라는 뜻이다.

## 변경 파일
- `backend/src/models/refresh_token.py` (신규): `RefreshToken` 모델
- `backend/src/models/user.py`: `refresh_tokens` 관계 추가 (T023에서 의도적으로 미룬 부분)
- `backend/src/models/__init__.py`: `RefreshToken` 내보내기 추가
- `backend/tests/unit/test_refresh_token_model.py` (신규): 컬럼·타입·NULL 허용·유일성·외래키 CASCADE·인덱스·기본값·양방향 관계·`passive_deletes`·`repr` 테스트 13개
- `specs/001-ai-code-learning-platform/tasks.md`: T024 완료 표시
- `docs/task-reports/TASK-024-RefreshToken-SQLAlchemy-모델.md` (신규): 작업 결과 기록

## TDD 결과
- RED 커밋: 해당 없음 (Git 저장소 아님). 구현 전 `from src.models import RefreshToken`이 `ImportError`로 실패하는 것을 확인했다.
- GREEN 커밋: 해당 없음. 구현 후 13개 통과, 기존 `test_user_model.py` 12개도 계속 통과.
- REFACTOR 커밋: 해당 없음.
- 테스트 커버리지: 백엔드 전체 98% (`refresh_token.py`, `user.py` 모두 100%). 전체 193개 통과, 25개 스킵(PostgreSQL 필요). ruff, black, mypy(strict) 통과.

## 기술 결정
- **`TimestampMixin`을 쓰지 않음**: 이 테이블에는 `updated_at`이 없다(토큰은 만들고, 폐기하고, 끝). 믹스인을 쓰면 마이그레이션에 없는 컬럼이 생기므로 `created_at`만 직접 선언했다.
- **`revoked`에 파이썬 기본값(`default=False`)도 지정**: 서버 기본값만 있으면 객체를 만들고 DB에 저장하기 전까지 `token.revoked`가 `None`이다. T026(TokenService)이 "폐기 여부"를 읽을 때 `None`과 `False`를 구분해야 하는 혼란을 막으려고 둘 다 두었다.
- **`revoked`는 NOT NULL로 선언**: 마이그레이션은 `DEFAULT FALSE`만 있고 NOT NULL은 없다. 모델 쪽이 더 엄격하지만, `bool`에 `NULL`이 끼면 "폐기됨/아님/모름"의 세 상태가 생겨 로직이 복잡해지므로 `Mapped[bool]`로 두었다. T023의 타임스탬프와 같은 판단이다.
- **`token_hash`에 해시를 직접 만드는 코드는 넣지 않음**: SHA-256 계산은 TokenService(T026)의 책임이다. 모델은 데이터 구조만 정의한다(헌법 III: 모델 레이어는 구조와 관계만).
- **순환 import 회피**: `User`와 `RefreshToken`이 서로 참조하므로 `TYPE_CHECKING` 안에서만 import하고 관계는 문자열 이름으로 연결했다. 두 모델은 `src/models/__init__.py`에서 함께 불러와 매퍼가 항상 짝을 찾는다.
- **`repr`에서 `token_hash` 제외**: 로그에 객체가 찍혀도 지문이 남지 않도록 했다.

## 비고
- **DB 연동 검증은 하지 못했다.** T023과 같이 Docker/PostgreSQL이 꺼져 있어 실제 `INSERT`, 유일성 위반, `ON DELETE CASCADE` 동작은 확인하지 못했다. 모델이 마이그레이션과 같은지는 메타데이터 수준(컬럼·타입·외래키·인덱스 이름)에서만 확인했다. DB를 켠 뒤 T025/T026 통합 테스트에서 확인하길 권한다.
- **중복 인덱스**: `token_hash`에 UNIQUE가 이미 있어 `idx_refresh_tokens_hash`는 중복이다. 마이그레이션이 만드는 그대로 모델도 따랐다(T023의 `idx_users_email`과 같은 경우).
- **`relationship`의 로딩 방식은 기본값(지연 로딩)**: 비동기 세션에서 `user.refresh_tokens`에 바로 접근하면 오류가 날 수 있다. 서비스(T025/T026)에서는 필요한 쿼리를 직접 작성하거나 `selectinload`를 명시하는 것이 안전하다.
- Git 저장소가 아니라 커밋은 없다.
