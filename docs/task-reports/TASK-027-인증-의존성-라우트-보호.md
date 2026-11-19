# TASK-027. 인증 의존성 (라우트 보호)

## 상태
완료

## 날짜
2026-11-06

## 작업 요약
보호가 필요한 API 앞에 세워 두는 "출입문 경비원" `get_current_user`를 만들었다. 경비원은 요청이 올 때마다 `Authorization: Bearer <액세스 토큰>` 헤더에서 방문증을 꺼내 진짜인지 확인하고(T026의 `verify_access_token`), 방문증에 적힌 사용자가 지금도 회원 명부(DB)에 있는지 확인한 뒤, 통과시킬 때 "이 사람은 누구입니다"라는 `User` 객체를 안으로 넘겨준다. 앞으로 API를 만들 때 `user: CurrentUser` 한 줄만 인자에 적으면 그 API가 로그인 필수가 된다.

```python
@router.get("/auth/me")
async def me(user: CurrentUser) -> ...:   # 로그인하지 않으면 여기까지 오지 못함
```

| 상황 | 결과 |
|------|------|
| 유효한 토큰 + 존재하는 사용자 | `User`를 라우트에 전달 |
| 헤더 없음, `Basic ...` 등 Bearer가 아닌 헤더, 빈 토큰 | 401 "로그인이 필요합니다" |
| 형식이 잘못됐거나 서명이 틀린 토큰, 리프레시 토큰을 낸 경우 | 401 "인증 정보가 올바르지 않습니다" |
| 만료된 토큰 | 401 "로그인 시간이 만료되었습니다" |
| 유효한 토큰인데 사용자가 삭제됨 | 401 "인증 정보가 올바르지 않습니다" |

## 변경 파일
- `backend/src/api/dependencies.py` (신규): `get_current_user`, `CurrentUser`
- `backend/src/services/auth/user_service.py`: `get_by_id(user_id)` 추가 (사용자 조회 전용)
- `backend/tests/unit/test_auth_dependency.py` (신규): 13개 케이스
- `backend/tests/unit/test_user_service.py`: `get_by_id` 테스트 2개 추가 (기존 테스트는 수정하지 않음)
- `specs/001-ai-code-learning-platform/tasks.md`: T027 완료 표시
- `docs/task-reports/TASK-027-인증-의존성-라우트-보호.md` (신규): 이 보고서

## TDD 결과
- RED 커밋: 해당 없음 (Git 저장소 아님). 구현 전 `src.api.dependencies` 모듈이 없어 `ModuleNotFoundError`, `get_by_id`는 `AttributeError`로 실패하는 것을 확인했다.
- GREEN 커밋: 해당 없음. 구현 후 전부 통과.
- REFACTOR 커밋: 해당 없음. 고칠 부분이 없었다.
- 테스트 커버리지: 백엔드 전체 100% (`dependencies.py` 100%). 전체 289개 통과(DB가 켜져 있어 전에 스킵되던 통합 테스트 25개도 실행됨). ruff, black, mypy(strict) 통과.
- 실제 PostgreSQL 확인: 임시 DB에서 유효 토큰 200, 헤더 없음·리프레시 토큰·만료 토큰·삭제된 사용자 401을 확인했다. 사용자를 삭제하면 `ON DELETE CASCADE`로 리프레시 토큰도 함께 사라지는 것도 확인했다.

## 기술 결정
- **Bearer 헤더만 읽고 쿠키는 읽지 않음**: research.md는 액세스 토큰도 HttpOnly 쿠키라고 적었지만, 이미 만든 프런트엔드(T020, T021)는 액세스 토큰을 메모리에 두고 `Authorization: Bearer`로 보낸다. 실제 클라이언트와 맞췄다. 쿠키로 인증하면 다른 사이트가 사용자의 브라우저를 이용해 요청을 보내는 공격(CSRF)을 막는 장치(T199)가 먼저 필요한데, 헤더 방식은 그 위험이 없다. 리프레시 토큰만 쿠키에 두는 구성은 T029/T031에서 다룬다.
- **`HTTPBearer(auto_error=False)`**: FastAPI 기본값은 헤더가 없을 때 자체 오류를 내서 이 프로젝트의 오류 응답 형식(`error`, `message`)과 어긋난다. 직접 `UnauthorizedException`을 내서 형식을 통일했다. Swagger 문서(`/docs`)에는 "Authorize" 버튼이 생긴다.
- **사용자 조회는 `UserService.get_by_id`로**: 헌법 X-12는 API 계층이 DB에 직접 접근하는 것을 금지한다. 의존성에서 `session.get(User, id)`를 바로 쓰면 편하지만 그 규칙을 어기게 된다.
- **삭제된 사용자의 토큰도 거절**: 액세스 토큰은 서명만 보면 통과하므로, 계정이 삭제돼도 최대 15분 동안 살아 있다. 매 요청마다 사용자 존재를 확인해서 이 틈을 막았다. 대신 요청마다 쿼리가 1번 늘지만, 어차피 라우트가 `User`를 필요로 하는 경우가 대부분이다.
- **세션은 `get_session`을 그대로 사용**: FastAPI는 한 요청 안에서 같은 의존성을 한 번만 실행하므로 인증과 라우트가 같은 세션을 쓴다(테스트로 확인). 요청이 성공하면 커밋, 실패하면 롤백이 한 번에 적용된다.
- **`CurrentUser`를 별칭으로 제공**: `Annotated[User, Depends(get_current_user)]`를 라우트마다 쓰지 않아도 된다.

## 비고
- 테스트 작성 중 제 가정이 틀린 부분이 있었다. SQLAlchemy는 UUID를 쿼리 문자열에 하이픈 없는 형태(`4ee7d525b7dd…`)로 내보내는데, 처음에는 하이픈 형식으로 비교해서 2건이 실패했다. 구현은 맞았고 비교 형식만 `.hex`로 고쳤다. 확인하려던 내용(토큰의 사용자 ID로 조회하는가)은 그대로다.
- 401 응답에 `WWW-Authenticate: Bearer` 헤더는 붙이지 않았다. `AppError`가 헤더를 지원하지 않고 프런트엔드가 쓰지 않는다. 필요해지면 `AppError`에 헤더 인자를 넣는 별도 작업으로 다룬다.
- 속도 제한(`/auth/refresh` 분당 10회 등)과 인증 실패 로그(FR-110)는 이 태스크 범위가 아니다.
- 다음 태스크 T028~T031(인증 API)이 `/auth/me`(T029A)에서 `CurrentUser`를 처음 사용한다. T030(로그아웃)과 T031(갱신)은 쿠키의 리프레시 토큰을 읽으므로 이 의존성을 쓰지 않는다.
- Git 저장소가 아니라 커밋은 없다.
