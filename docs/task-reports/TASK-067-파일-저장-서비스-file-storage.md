# TASK-067. 파일 저장 서비스 file storage

## 상태
완료

## 날짜
2026-11-16

## 작업 요약
업로드된 코드를 `{UPLOAD_DIR}/{user_id}/{task_id}/{uuid}{확장자}`에 저장하는 파일 저장 모듈을 만들었다.

| 함수 | 역할 |
|------|------|
| `get_storage_root()` | `UPLOAD_DIR` 환경변수(기본 `storage/uploads`)를 절대 경로로 반환 |
| `save_file(user_id, task_id, extension, content)` | 파일을 쓰고 저장소 루트 기준 상대 경로(`CodeFile.storage_path`)를 반환 |
| `read_file(storage_path)` | 저장된 바이트를 읽음. 루트 밖 경로는 `FileValidationError(invalid_path)` |
| `delete_task_files(user_id, task_id)` | 태스크 디렉터리 삭제(없어도 오류 없음) |
| `safe_relative_path(path)` | 폴더 업로드의 클라이언트 상대 경로를 `/` 구분으로 정규화, `..`/절대경로/드라이브/NUL 거부 |

## 변경 파일
- `backend/src/services/code_analysis/file_storage.py` (신규)
- `backend/tests/unit/test_file_storage.py` (신규, 24개)
- `specs/001-ai-code-learning-platform/tasks.md` (T067 완료 표시)

## TDD 결과
- RED: 구현 전 테스트를 먼저 작성하고 실행해 수집 단계 오류(모듈/라우트 부재)로 실패함을 확인함
- GREEN: 최소 구현 후 통과 확인
- REFACTOR: black / ruff / mypy 통과 확인
- 전체 백엔드: 736 passed, 47 skipped (이전 608 passed, 43 skipped). skipped는 PostgreSQL이 필요한 통합 테스트로, 이 환경에 DB가 없어 실행되지 않음
- 커밋: Git 저장소가 아니라 없음
- 커버리지: `file_storage.py` 100%
- 이 태스크 테스트: 24개 통과

## 기술 결정
- 저장 파일명은 서버가 만든 UUID라 클라이언트 파일명이 파일시스템에 닿지 않는다(경로 이탈 원천 차단). 클라이언트 상대 경로는 DB 메타데이터(`file_path`)로만 저장하며 `safe_relative_path`가 검증한다. file_validator 보고서의 "경로 이탈 방어는 T067 책임" 항목을 이 모듈이 담당한다.
- `storage_path`는 루트 기준 상대 경로로 저장한다(data-model 예시는 `storage/uploads/...` 전체 경로). 루트를 옮겨도 DB를 고치지 않아도 되고, 읽을 때 루트 안 포함 여부를 다시 확인한다.
- 루트는 호출마다 환경변수에서 읽는다(테스트에서 tmp 경로 주입 가능, 별도 설정 객체 없음).

## 비고
- 동기 파일 I/O다. 업로드 한도가 10MB라 이벤트 루프 영향은 작다고 보고 `run_in_threadpool` 등은 쓰지 않았다.
- `.env.example`의 `UPLOAD_DIR=./storage/uploads`는 실행 디렉터리 기준 상대 경로다. 백엔드를 `backend/`에서 실행하면 `backend/storage/uploads`가 되므로 배포 시 절대 경로 지정을 권장한다.
