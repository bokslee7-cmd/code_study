# TASK-069. CodeUploadService 파일 폴더 붙여넣기 업로드

## 상태
완료

## 날짜
2026-11-16

## 작업 요약
업로드 3가지 방식을 검증하고 저장하는 서비스. 검증과 저장을 분리해, 잘못된 업로드가 태스크 번호를 쓰거나 디스크에 파일을 남기지 않게 했다.

| 메서드 | 동작 |
|--------|------|
| `prepare_files([(이름, 내용)])` | 파일 업로드 검증(`method=file`) |
| `prepare_folder([(상대경로, 내용)])` | 경로 정규화/이탈 거부, `.git`/`node_modules`/`__pycache__`/`.DS_Store` 제외(FR-017), `method=folder` |
| `prepare_paste(code, language)` | 언어 드롭다운 값 -> `code{확장자}` 파일, `method=paste` |
| `store(user_id, task, prepared)` | 파일 저장, `detect_dominant_language`/`analyze_complexity`로 `UploadedCode`와 `CodeFile` 행 추가 |
| `get_code(task)` | 파일 내용과 언어를 경로/이름순으로 반환, 업로드 없음 404 |

`FileValidationError`는 `AppError(error=code)`로 변환한다. 크기 초과(`file_too_large`, `upload_too_large`)는 413, 나머지는 400.

## 변경 파일
- `backend/src/services/code_analysis/code_upload_service.py` (신규)
- `backend/tests/unit/test_code_upload_service.py` (신규, 29개)
- `specs/001-ai-code-learning-platform/tasks.md` (T069 완료 표시)

## TDD 결과
- RED: 구현 전 테스트를 먼저 작성하고 실행해 수집 단계 오류(모듈/라우트 부재)로 실패함을 확인함
- GREEN: 최소 구현 후 통과 확인
- REFACTOR: black / ruff / mypy 통과 확인
- 전체 백엔드: 736 passed, 47 skipped (이전 608 passed, 43 skipped). skipped는 PostgreSQL이 필요한 통합 테스트로, 이 환경에 DB가 없어 실행되지 않음
- 커밋: Git 저장소가 아니라 없음
- 커버리지: `code_upload_service.py` 100%
- 이 태스크 테스트: 29개 통과

## 기술 결정
- 붙여넣기 언어 값: python, javascript, typescript, html, css, java, cpp, c, text, markdown (대소문자 무시). 그 외는 400 `unsupported_language`. 목록은 스펙에 없어 지원 확장자에서 정했다.
- 폴더 업로드에서 지원하지 않는 확장자/바이너리 파일이 섞이면 건너뛰지 않고 거부한다(FR-016 "명확한 오류"). 제외 대상은 FR-017 목록뿐이다.
- `store` 중 DB 쓰기가 실패하면 이미 쓴 파일을 지운다(고아 파일 방지). 요청 세션 롤백은 `get_session`이 담당한다.
- `UploadedCode(task=task)`로 관계를 양쪽에 설정해, 비동기 세션에서 lazy load 없이 `task.uploaded_code`를 응답에 쓸 수 있다.
- `mime_type`은 항상 `text/plain`(바이너리는 이미 거부됨, OS별 mimetypes 차이 회피).

## 비고
- `get_code` 정렬은 `file_path`, `file_name`이다. 같은 트랜잭션 안에서는 `created_at`이 모두 같아 업로드 순서를 복원할 수 없다.
- 파일 간 의존성/선수 개념(FR-022, FR-023)은 이 태스크 범위가 아니다.
