# TASK-007. Git 무시 패턴(.gitignore) 설정

## 상태
완료

## 날짜
2026-10-29

## 작업 요약
루트 `.gitignore`를 만들었다. node_modules, venv(.venv), `__pycache__`, 캐시(pytest/mypy/ruff), 빌드·커버리지 산출물, `.env*`(예시 파일 `!.env.example`은 추적), `storage/uploads/`, 로그, OS·에디터 파일을 제외한다.

## 변경 파일
- .gitignore (신규)
- storage/uploads/.gitkeep (신규, 빈 파일)

## TDD 결과
- RED 커밋: 해당 없음 (Git 저장소 아님). 파일 없는 상태에서 9개 실패 확인.
- GREEN 커밋: 해당 없음. 패턴 8개와 `.env.example` 예외 테스트 통과.
- REFACTOR 커밋: 해당 없음
- 테스트 커버리지: 해당 없음

## 기술 결정
- **`.env.*` + `!.env.example`**: 실제 환경 파일은 막고 템플릿만 추적한다(constitution V 보안).
- **`storage/uploads/` 전체 무시**: 업로드 파일은 커밋하지 않는다. 이 때문에 `.gitkeep`도 추적되지 않으므로, 디렉터리 유지가 필요하면 앱 시작 시 생성하도록 해야 한다.

## 비고
- **실제 `git check-ignore`로는 검증하지 못했다.** 이 프로젝트는 아직 Git 저장소가 아니다(`git init` 필요). 테스트는 패턴 문자열 존재만 확인한다.
- `.vscode/`는 팀 설정을 공유할 수 있어 무시하지 않았다.
- Phase 1(Setup) 완료. 다음 작업: Phase 2 T008(Alembic).
