# TASK-005. 환경변수 템플릿(.env.example) 생성

## 상태
완료

## 날짜
2026-10-29

## 작업 요약
루트 `.env.example`(백엔드·Docker 공용)과 `frontend/.env.example`(Vite용)을 만들었다. 키는 quickstart.md 기준이다: DB, Redis, Google API 키, JWT 비밀키 2개, 환경/디버그/CORS, 업로드 경로·용량.

## 변경 파일
- .env.example (신규)
- frontend/.env.example (신규)
- backend/tests/unit/test_project_config.py (신규, T005·T006·T007 공용)

## TDD 결과
- RED 커밋: 해당 없음 (Git 저장소 아님). 파일 없는 상태에서 실패 확인.
- GREEN 커밋: 해당 없음. 필수 키 존재, 비밀값이 플레이스홀더인지, 프론트 키 존재 3개 테스트 통과.
- REFACTOR 커밋: 해당 없음
- 테스트 커버리지: 해당 없음 (설정 파일)

## 기술 결정
- **호스트를 localhost로**: quickstart는 `db`/`redis` 호스트를 쓰지만 백엔드를 로컬에서 실행하므로 localhost로 했다. 백엔드를 컨테이너로 옮길 때 바꾼다(주석으로 안내).
- **비밀값은 플레이스홀더**(`change-me-…`, `your-…`): 테스트가 실제 비밀 커밋을 막는다.

## 비고
- 실제 `.env`는 아직 만들지 않았다. 사용 시 `cp .env.example .env` 후 `GOOGLE_API_KEY`, JWT 키를 채운다.
- DB 비밀번호 기본값 `postgres`는 개발용이다.
