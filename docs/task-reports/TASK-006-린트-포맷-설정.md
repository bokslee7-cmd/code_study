# TASK-006. 린트·포맷 설정 (Ruff/Black/MyPy, ESLint/Prettier)

## 상태
완료

## 날짜
2026-10-29

## 작업 요약
- 백엔드 `backend/pyproject.toml`: Black(line 100), Ruff(E,F,I,UP,B), MyPy strict, pytest 설정
- 프론트엔드: `eslint.config.js`(ESLint 9 flat config, typescript-eslint, react-hooks, react-refresh, eslint-config-prettier), `.prettierrc`, `.prettierignore`
- `package.json` 스크립트: `lint`, `format`
- Prettier로 기존 프론트 소스를 한 번 정리하고 lint 오류 0건 확인

## 변경 파일
- backend/pyproject.toml (신규)
- frontend/eslint.config.js, .prettierrc, .prettierignore (신규)
- frontend/package.json, package-lock.json (수정)

## TDD 결과
- RED 커밋: 해당 없음 (Git 저장소 아님). 설정 파일 없는 상태에서 실패 확인.
- GREEN 커밋: 해당 없음. pyproject(ruff·black·mypy strict), eslint/prettier 설정, lint·format 스크립트 3개 테스트 통과.
- REFACTOR 커밋: 해당 없음
- 테스트 커버리지: 해당 없음

추가 검증: `npm run lint` 오류 없음, `tsc -b` 통과, 프론트 테스트 1개 통과.

## 기술 결정
- **ESLint 9 (flat config)**: constitution V가 `eslint.config.js`를 지정한다. quickstart의 ESLint 8.54와 다르다. `@eslint/js`는 `^9`로 맞춰야 peer 충돌(ERESOLVE)이 나지 않는다.
- **Ruff/Black 줄 길이 100**으로 통일.

## 비고
- **백엔드 린트는 실제로 실행하지 못했다.** ruff/black/mypy를 설치하지 않았고 `backend/src`도 비어 있어 설정 파일 존재만 테스트했다. 코드가 생기는 T010 이후 `ruff check src/`, `black --check src/`, `mypy src/`를 돌려야 한다.
- `pyproject.toml`의 `asyncio_mode`는 pytest-asyncio가 설치된 환경에서만 인식된다(임시 venv에서는 경고).
- `npm audit`가 취약점 10건(critical 4)을 보고했다. 개발 의존성 위주로 보이나 아직 조사하지 않았다.
