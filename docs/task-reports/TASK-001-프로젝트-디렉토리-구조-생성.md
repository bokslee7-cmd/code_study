# TASK-001. 프로젝트 디렉토리 구조 생성

## 상태
완료

## 날짜
2026-10-27

## 작업 요약
plan.md의 Project Structure와 constitution III(Modular Monolith)에 맞춰 backend/, frontend/, storage/, docs/ 디렉토리를 생성했다.
- backend/src: models, api, db, utils, tasks, services(auth, code_analysis, ai, document, practice, qa, progress)
- backend/tests: contract, integration, unit
- frontend/src: components(auth, project, task, upload, document, practice, qa, progress), pages, services, hooks, utils, lib, stores
- frontend/tests: integration, unit
- storage/uploads, docs/task-reports

빈 디렉토리가 추적되도록 각 말단 디렉토리에 `.gitkeep`을 추가했다. 총 43개 디렉토리.

## 변경 파일
- backend/**, frontend/**, storage/uploads/, docs/ 하위 디렉토리 및 `.gitkeep` 파일 (소스 코드 없음)

## TDD 결과
- RED 커밋: 해당 없음
- GREEN 커밋: 해당 없음
- REFACTOR 커밋: 해당 없음
- 테스트 커버리지: 해당 없음

예외 사유: 코드가 없는 디렉토리 생성 작업이라 단위 테스트 대상이 없다. 대신 주요 경로의 존재 여부를 셸 명령으로 직접 검증했다(7개 경로 모두 OK). 또한 현재 작업 폴더는 Git 저장소가 아니라 커밋을 만들지 못했다.

## 기술 결정
- `frontend/src/stores`, `frontend/src/lib`는 plan.md 트리에는 없지만 tasks.md의 T019(queryClient), T021(auth-store) 경로에 필요해 미리 만들었다.
- 모든 경로는 `/` 구분자로 `mkdir -p`를 사용했다(Git Bash 호환).

## 비고
- 다음 작업: T002(backend requirements.txt), T003(Vite 프론트엔드 초기화). T003의 Vite 템플릿이 비어있지 않은 frontend/를 거부하면 `.gitkeep` 정리가 필요할 수 있다.
- Git 저장소 초기화가 아직 안 되어 있다. constitution VI의 커밋 규칙을 따르려면 `git init` 또는 기존 저장소 연결이 필요하다.
