# TASK-T086. 브라우저 테스트: 코드 붙여넣기와 언어 감지

## 상태
완료

## 날짜
2026-11-16

## 작업 요약
'코드 붙여넣기' 탭에서 언어를 python으로 고르고 4줄짜리 Python 코드를 붙여넣어 생성한 뒤 서버에 저장된 언어 감지 결과를 확인했다.

## 변경 파일
- 없음 (수동 브라우저 테스트). 스크립트·스크린샷은 세션 스크래치 폴더에 있고 저장소에는 넣지 않았다.
- `specs/001-ai-code-learning-platform/tasks.md` (T086 완료 표시)

## TDD 결과
- 해당 없음(수동 브라우저 테스트). 결과: **통과**
- 서버 저장값: detected_language=python, complexity_level=beginner, total_lines=4, 파일 code.py(python). 태스크 번호 Task 3.

## 기술 결정
- 실행 환경: Docker(PostgreSQL 15, Redis 7) + uvicorn(8000) + Vite(5173), Chromium headless, Playwright 1.49.1. 세션에 Playwright MCP 도구가 연결되지 않아 스크래치 폴더에 Playwright를 따로 설치해 같은 엔진으로 스크립트를 실행했다(프로젝트에는 설치하지 않음).
- 테스트 계정은 실행마다 새 이메일로 회원가입해 만들었다.

## 비고
- 이 테스트는 사용자가 언어를 직접 고른 경로다. 언어를 '선택 안 함'으로 두거나 확장자 없는 코드의 자동 감지(Pygments 단계)는 이 화면에서 시험하지 않았다.
- 언어 감지 결과는 화면에 표시되는 곳이 없어 API 응답으로 확인했다(TaskDetail은 아직 골격).
