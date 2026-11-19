# TASK-057 ~ 060. 프로젝트 관리 브라우저 수동 테스트

## 상태
부분 완료 (T057, T058 통과 / T059, T060은 브라우저 UI 부재로 API 검증만 수행 — 보류)

## 날짜
2026-11-12

## 작업 요약
Docker Desktop을 켜서 기존 개발용 컨테이너(`1027_speckit-db-1`, `1027_speckit-redis-1`)를 기동하고, 백엔드(`127.0.0.1:8000`)와 프런트엔드(`localhost:5173`)를 띄운 뒤 Chrome에서 프로젝트 관리 흐름을 확인했다.

도구는 **Claude in Chrome 확장**을 썼다. 요청은 Playwright MCP였지만 이 세션에는 연결돼 있지 않아서, 사용자가 확인한 뒤 Chrome 확장으로 대체했다.

| 태스크 | 확인한 것 | 방법 | 결과 |
|--------|-----------|------|------|
| T057 | "새 프로젝트" 모달에서 제목·설명 입력 후 생성 → 대시보드에 카드 표시 | 브라우저 UI | 통과. `POST /projects` 201, 카드에 제목·설명·`0/0 테스크 완료 0%`·마지막 활동일 표시 |
| T058 | 카드 클릭 → 상세 페이지 | 브라우저 UI | 통과. 제목, 설명, 생성일, 진행률 바, "태스크 타임라인(준비 중)" 표시 |
| T059 | 제목 수정 후 영속 확인 | **API(curl)만** | 화면에 수정 UI 없음. `PATCH /projects/{id}` 200, 재조회 시 새 제목 유지. 빈 제목은 400 `validation_error` |
| T060 | 삭제 후 소프트 삭제·휴지통 확인 | **API(curl)·DB만** | 화면에 삭제 UI 없음. `DELETE` 204, 이후 상세 404·목록 0건, DB에서 `deletion_status='trashed'`, `trashed_at` 기록, `scheduled_deletion_at`은 30일 뒤 |

### T059·T060을 완료 처리하지 않은 이유
- 프런트엔드에 프로젝트 수정·삭제 버튼/화면이 없다(`ProjectCard`, `ProjectDetail`, `Dashboard`에서 확인). `project-service.ts`에 `updateProject`/`deleteProject` 함수만 있다.
- "휴지통 가시성"은 `/trash` 라우트가 `PagePlaceholder`(제목 "휴지통"만 표시)이고, 백엔드 `/trash` API도 404다. 휴지통 기능은 T170+ 범위(`project_service.py` 주석 참고).
- 따라서 "브라우저에서 수정/삭제하고 휴지통에서 확인"이라는 태스크 문장은 현재 코드로 수행할 수 없다. 백엔드 동작(영속성, 소프트 삭제)은 확인했으나 브라우저 검증은 아니라서 [X]로 표시하지 않았다.

## 변경 파일
- `specs/001-ai-code-learning-platform/tasks.md`: T057, T058 완료 표시, T059·T060에 보류 사유 주석
- `docs/task-reports/TASK-057-프로젝트-관리-브라우저-수동-테스트.md`: 이 보고서
- 코드 변경 없음

## TDD 결과
해당 없음(수동 테스트 태스크).

## 기술 결정
- 백엔드는 `.env` 없이 환경변수(`DATABASE_URL`, `REDIS_URL`, `JWT_SECRET_KEY`, `JWT_REFRESH_SECRET`, `ALLOWED_ORIGINS`, `COOKIE_SECURE=false`)로 기동했다. JWT 비밀키는 이번 실행용 임시 값이다.
- 테스트 계정은 `.env.example`의 `TEST_USER_EMAIL`/`TEST_USER_PASSWORD`(기존 DB 계정 `browser-test@example.com`)를 썼다.
- Git Bash에서 `curl -d`로 한글 JSON을 보내면 400("error parsing the body")이 난다(셸 인코딩 문제, 백엔드 버그 아님). UTF-8 파일을 `--data-binary @file`로 보내면 정상 처리된다.

## 비고
- 개발 DB에 테스트 프로젝트(제목 "T059 수정된 제목", 상태 `trashed`)가 남아 있다. 휴지통 기능 구현 전까지 화면에서는 보이지 않는다.
- 후속 필요 작업(제안): 프로젝트 수정·삭제 UI(예: 상세 페이지의 수정/삭제 버튼, 삭제 확인 모달)와 휴지통 페이지 구현 후 T059·T060을 브라우저에서 다시 확인.
- Git 저장소가 아니라 커밋은 없다.
