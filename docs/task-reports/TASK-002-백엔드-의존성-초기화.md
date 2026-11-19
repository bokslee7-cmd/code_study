# TASK-002. 백엔드 Python 프로젝트 의존성 초기화

## 상태
완료

## 날짜
2026-10-27

## 작업 요약
`backend/requirements.txt`를 작성했다. quickstart.md의 패키지 목록을 기반으로 하고, 이후 태스크에 필요한 항목을 추가했다.
- 웹: fastapi, uvicorn, pydantic, pydantic-settings, python-multipart, httpx
- DB: sqlalchemy[asyncio], asyncpg, alembic
- 인증: python-jose, passlib[bcrypt], bcrypt
- AI: google-generativeai
- 비동기: celery[redis], redis
- 코드 분석: pygments
- 테스트: pytest, pytest-asyncio, pytest-cov
- 품질(constitution V): ruff, black, mypy

## 변경 파일
- backend/requirements.txt (신규)

## TDD 결과
- RED 커밋: 해당 없음
- GREEN 커밋: 해당 없음
- REFACTOR 커밋: 해당 없음
- 테스트 커버리지: 해당 없음

예외 사유: 설정 파일 작업이라 단위 테스트 대상이 없다. 대신 `pip install --dry-run -r requirements.txt`(Python 3.12.10)로 의존성 해석이 충돌 없이 성공함을 검증했다. 실제 설치는 하지 않았다. Git 저장소가 아니라 커밋도 없다.

## 기술 결정
- **redis 5.0.1 → 4.6.0**: quickstart.md의 `celery[redis]==5.3.4`와 `redis==5.0.1`은 서로 충돌한다(celery 5.3.4는 redis<5.0.0 요구). dry-run에서 ResolutionImpossible이 발생해 redis를 4.6.0으로 낮췄다.
- **bcrypt==4.0.1 고정**: passlib 1.7.4는 bcrypt 4.1 이상과 호환되지 않는다.
- **pydantic-settings 추가**: T011(DB 설정)에서 환경변수 기반 설정에 사용 예정.
- **ruff/black/mypy 추가**: constitution V의 린트·타입 요구. 설정(pyproject.toml)은 T006에서 한다.

## 비고
- `google-generativeai==0.3.0`은 오래된 SDK다. 프로젝트가 쓰기로 한 Gemini 3 Flash Preview 모델을 이 버전이 지원하는지 확인되지 않았다. AI 서비스 구현 태스크 전에 최신 SDK(`google-genai`)로 교체할지 검토가 필요하다.
- 나머지 핀 버전은 2023년 기준이라 오래되었다. 보안 업데이트 반영은 별도 판단이 필요하다.
- 가상환경 생성과 설치는 하지 않았다. 필요할 때 `python -m venv venv && pip install -r requirements.txt`.
- 다음 작업: T003(Vite 프론트엔드 초기화).
