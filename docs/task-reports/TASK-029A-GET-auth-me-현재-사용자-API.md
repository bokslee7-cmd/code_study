# TASK-029A. GET /auth/me (현재 사용자 API)

## 상태
완료

## 날짜
2026-11-09

## 작업 요약
"나는 지금 누구로 로그인되어 있지?"를 묻는 안내 데스크를 만들었다. T027에서 만든 출입문 경비원(`CurrentUser`)을 처음으로 실제 라우트에 세웠다. 경비원이 일일 이용권을 확인하고 `User`를 건네주면, 라우트는 그 사람의 공개 정보 3가지(`id`, `email`, `skill_level`)만 응답한다. 포장지(`{"user": ...}`) 없이 사용자 객체 자체를 돌려준다.

| 상황 | 결과 |
|------|------|
| 유효한 액세스 토큰 | 200 `{"id", "email", "skill_level"}` |
| `skill_level`이 비어 있음 | 200, 값은 `null` |
| 헤더 없음 | 401 |
| 리프레시 토큰을 낸 경우 | 401 |

## 변경 파일
- `backend/src/api/auth.py`: `me` 라우트 (`user: CurrentUser` 한 줄로 로그인 필수)
- `backend/tests/unit/test_auth_api.py`: `/me` 5개 케이스
- `docs/task-reports/TASK-029A-GET-auth-me-현재-사용자-API.md` (신규): 이 보고서

## TDD 결과
- RED 커밋: 해당 없음 (Git 저장소 아님). 구현 전 `tests/unit/test_auth_api.py`가 `src.api.auth_cookies` 모듈이 없어 `ImportError`(수집 단계 실패)로 멈추는 것을 확인했다.
- GREEN 커밋: 해당 없음. 구현 후 `test_auth_api.py` 50개 통과.
- REFACTOR 커밋: 해당 없음. `UserResponse`를 가입, 로그인 응답과 공유해서 사용자 모양이 한 곳에서만 정의되도록 했다.
- 테스트 커버리지: 신규 코드(`auth.py`, `auth_cookies.py`, `schemas/auth.py`, `dependencies.py`) 100%. 백엔드 전체 314개 통과, 25개 스킵(Docker/DB가 꺼져 있어 DB 통합 테스트가 스킵됨), ruff, black, mypy(strict) 통과.

## 기술 결정
- **`CurrentUser`는 가짜로 바꾸지 않고 진짜 의존성을 그대로 사용**: 세션만 가짜로 바꿔서 토큰 검증, 사용자 조회, 응답 변환이 이어진 상태를 확인했다.
- **`response_model=UserResponse`로 필드 제한**: ORM 객체를 그대로 반환하지 않고 스키마로 변환하므로 `password_hash`, `last_login_at` 등 내부 값이 응답에 섞일 수 없다(응답 키가 정확히 3개임을 테스트).
- **`from_attributes=True`**: ORM `User`를 `UserResponse.model_validate`로 바로 변환한다.

## 비고
- 인증 실패 사유별 메시지(만료, 잘못된 토큰)는 T027 테스트가 이미 검증하므로 여기서는 헤더 없음과 리프레시 토큰 거부만 대표로 확인했다.
- Git 저장소가 아니라 커밋은 없다.
