# TASK-T085. 브라우저 테스트: 폴더 업로드

## 상태
완료

## 날짜
2026-11-16

## 작업 요약
proj/src/main.py, proj/src/util.py와 제외 대상인 proj/node_modules/skip.js, proj/.git/config가 든 폴더를 올려 구조가 보존되고 제외 폴더가 빠지는지 확인했다.

## 변경 파일
- 없음 (수동 브라우저 테스트). 스크립트·스크린샷은 세션 스크래치 폴더에 있고 저장소에는 넣지 않았다.
- `specs/001-ai-code-learning-platform/tasks.md` (T085 완료 표시)

## TDD 결과
- 해당 없음(수동 브라우저 테스트). 결과: **통과**
- 모달 안내: '2개 항목은 자동으로 제외했습니다. (.git, node_modules, __pycache__, .DS_Store)'. 서버 저장 경로(GET /tasks/{id}/code의 file_path): ["proj/src/main.py", "proj/src/util.py"]. 태스크 번호는 Task 2.

## 기술 결정
- 실행 환경: Docker(PostgreSQL 15, Redis 7) + uvicorn(8000) + Vite(5173), Chromium headless, Playwright 1.49.1. 세션에 Playwright MCP 도구가 연결되지 않아 스크래치 폴더에 Playwright를 따로 설치해 같은 엔진으로 스크립트를 실행했다(프로젝트에는 설치하지 않음).
- 테스트 계정은 실행마다 새 이메일로 회원가입해 만들었다.

## 비고
- 이 테스트는 Playwright의 디렉터리 업로드(webkitdirectory 입력에 폴더 경로 전달)로 수행했다. 실제 사용자가 폴더 선택 대화상자로 고르는 경로와 브라우저 내부 구현은 같지만 OS 대화상자는 거치지 않았다.
