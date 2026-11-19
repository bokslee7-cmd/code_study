# TASK-063. CodeFile SQLAlchemy 모델

## 상태
완료

## 날짜
2026-11-12

## 작업 요약
`code_files` 테이블에 대응하는 `CodeFile` 모델을 만들었다. 업로드된 소스 파일 한 개의 메타데이터(파일명, 폴더 내 상대 경로, 확장자, 크기, 저장 경로, MIME 타입)를 담고, 파일 본문은 `storage_path`가 가리키는 파일시스템에 있다. 컬럼·NULL 허용 여부, 지원 확장자 체크 `supported_extension`(12종: `.py .js .ts .jsx .tsx .html .css .java .cpp .c .txt .md`), `idx_code_files_uploaded_code_id` 인덱스를 T009 마이그레이션과 같은 이름으로 맞췄다. `UploadedCode.code_files` ↔ `CodeFile.uploaded_code` 양방향 관계를 추가했고, 삭제는 DB `ON DELETE CASCADE`에 맡긴다(`passive_deletes`).

## 변경 파일
- `backend/src/models/code_file.py` (신규)
- `backend/src/models/uploaded_code.py` (`code_files` 관계 추가)
- `backend/src/models/__init__.py` (`CodeFile` export)
- `backend/tests/unit/test_code_file_model.py` (신규, 14개 테스트)
- `specs/001-ai-code-learning-platform/tasks.md` (T063 완료 표시)

## TDD 결과
- RED: `from src.models import CodeFile` ImportError로 수집 단계 실패 확인
- GREEN: 신규 14개 통과(모델 3종 합계 44개), 전체 백엔드 501개 통과
- REFACTOR: ruff·black·mypy(src/models) 통과
- 테스트 커버리지: `src/models/code_file.py` 100%
- 커밋: Git 저장소가 아니라 없음

## 기술 결정
- `updated_at`이 없는 테이블이라 `TimestampMixin`을 쓰지 않고 `created_at`만 직접 선언했다(T062와 동일).
- 확장자 목록은 `SUPPORTED_EXTENSIONS` 한 곳에 두고 체크 제약 SQL과 클래스 상수가 함께 쓰게 했다. 이후 파일 검증기(T0xx)가 같은 상수를 재사용할 수 있다.
- `file_extension`은 NULL을 허용한다(마이그레이션이 NOT NULL이 아님). SQL `IN` 체크는 NULL을 통과시키므로 확장자 없는 파일은 DB가 막지 않는다. 확장자 검증은 업로드 검증 서비스의 책임이다.
- 개발 DB에 사용자→프로젝트→태스크→UploadedCode→CodeFile을 flush해 스키마 일치를 확인했고, `.exe` 확장자는 IntegrityError로 거부되는 것도 확인했다(롤백해서 데이터는 남지 않음).

## 비고
- 이 태스크로 Phase 5의 모델 3종(T061~T063)이 모두 끝났다.
- 다음: Phase 5의 후속 태스크(서비스·API·업로드 컴포넌트).
