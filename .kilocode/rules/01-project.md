# 프로젝트 공통 규칙 (code_study / AI Code Learning Platform)

이 파일은 Kilo Code가 모든 모드에서 자동으로 읽는 프로젝트 규칙이다.
원본은 루트의 `CLAUDE.md`와 `.specify/memory/constitution.md`이며, 충돌 시 constitution이 우선한다.

## 기술 스택

- Backend: Python 3.11+, FastAPI, PostgreSQL, SQLAlchemy 2.0, Celery, Redis
- AI: Google Gemini 3 Flash Preview API
- Frontend: TypeScript, React 18+, TanStack Query
- 저장소: `storage/uploads/` (코드 파일, 파일시스템, git 제외)

## 디렉터리 구조

```text
backend/src/     # FastAPI 소스
backend/tests/   # pytest
frontend/src/    # React 소스
frontend/tests/  # Vitest
specs/           # 기능별 spec / plan / tasks
.specify/        # Spec Kit 템플릿, 스크립트, constitution
```

## 명령어 (Windows PowerShell 기준)

```powershell
cd backend; pytest; ruff check src/
cd frontend; npm test
```

PowerShell 5.1에서는 `&&`를 쓸 수 없으므로 `;`로 연결한다.

## 작업 방식

- 먼저 `.specify/memory/constitution.md`를 읽고 원칙을 따른다.
- 기능 작업은 `specs/<번호>-<이름>/`의 `spec.md` → `plan.md` → `tasks.md` 순서를 따른다.
- Spec Kit 단계는 워크플로우로 실행한다: `/speckit.specify.md`, `/speckit.plan.md`, `/speckit.tasks.md`, `/speckit.implement.md` 등.
- TDD: 테스트를 먼저 쓰고(Red) 최소 구현으로 통과시킨다(Green). 모드는 `tdd-test-architect` → `backend-tdd-implementation` / `frontend-tdd-implementer` 순서.
- 사용자에게는 한국어로 응답한다. 코드 식별자와 기술 용어는 원문을 유지한다.
- `.env`, `storage/uploads/`는 커밋하지 않는다. 비밀 값은 `.env.example`에만 키 이름으로 둔다.
