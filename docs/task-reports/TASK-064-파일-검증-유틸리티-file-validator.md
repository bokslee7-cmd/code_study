# TASK-064. 파일 검증 유틸리티 (file_validator)

## 상태
완료

## 날짜
2026-11-12

## 작업 요약
코드 업로드의 "문 앞 검문소"를 만들었다. I/O 없는 순수 함수 모음이며, 규칙을 어기면 `FileValidationError`(`ValueError` 하위, 안정적인 `code` + 사용자에게 보여줄 한국어 메시지)를 던진다. API 계층(T071)이 `code`로 응답을 매핑하면 된다.

| 함수 | 역할 | 에러 code |
|------|------|-----------|
| `get_extension` | 소문자 확장자(점 포함). 점 파일·확장자 없음·끝이 점이면 빈 문자열 | - |
| `validate_extension` | 12종 화이트리스트(FR-015), 대소문자 무시 | `unsupported_extension` |
| `validate_size` | 파일 크기 10MB 이하(FR-014) | `file_too_large`, `invalid_size` |
| `is_binary` / `validate_not_binary` | 바이너리 거부(FR-016) | `binary_file` |
| `validate_file_count` | 1~20개(FR-018) | `no_files`, `too_many_files` |
| `validate_code_file` | 파일 1개 검사(확장자 → 크기 → 내용), 확장자 반환 | 위 코드들 |
| `validate_upload` | 업로드 전체 검사(개수 → 합계 10MB → 파일별), 확장자 목록 반환 | + `upload_too_large` |
| `is_excluded_path` | `.git`, `node_modules`, `__pycache__` 폴더 제외 판정(스펙 엣지 케이스) | - |

바이너리 판정: 앞 8000바이트에서 ① 알려진 시그니처(PNG, JPEG, GIF, PDF, ZIP/JAR/DOCX, ELF) ② NUL 바이트 ③ UTF-8로 해석 불가 중 하나라도 해당하면 바이너리.

## 변경 파일
- `backend/src/utils/file_validator.py` (신규)
- `backend/tests/unit/test_file_validator.py` (신규, 75개 테스트)
- `specs/001-ai-code-learning-platform/tasks.md` (T064 완료 표시)

## TDD 결과
- RED: `src.utils.file_validator` 모듈 부재로 수집 단계 실패 확인
- GREEN: 1차 실행에서 74/75 통과. 테스트가 실제 버그를 잡음 — `"trailing."` 파일명이 확장자 `"."`로 반환됨 → 끝이 점이면 빈 문자열로 수정 후 75/75 통과
- REFACTOR: ruff·black·mypy 통과
- 테스트 커버리지: `file_validator.py` 100%
- 전체 백엔드 576개 통과
- 커밋: Git 저장소가 아니라 없음

## 기술 결정
- 확장자 목록·10MiB 상수는 `CodeFile.SUPPORTED_EXTENSIONS`, `UploadedCode.MAX_UPLOAD_SIZE_BYTES`(DB 제약과 같은 값)를 재사용해 한 곳에서만 정의한다. 검증기와 DB 체크 제약이 어긋날 수 없다.
- UTF-8 디코딩은 `final=False` 증분 디코더를 쓴다. 8000바이트 샘플 경계에서 한글 같은 멀티바이트 문자가 잘려도 바이너리로 오판하지 않는다(테스트로 고정).
- 시그니처 목록에 `MZ`(Windows 실행 파일)는 넣지 않았다. 텍스트 파일이 "MZ"로 시작할 수 있고, 실제 실행 파일은 NUL 바이트로 걸러진다.
- 에러 메시지는 요구사항 문서(requirements-addendum)의 한국어 문구에 맞췄다. 한글 폭 계산이 black(1칸)과 ruff(2칸)에서 달라 긴 문구는 `" ".join((...))` 형태로 나눠 두 도구 모두 통과시켰다.
- 합계 10MB 검사를 파일별 내용 검사보다 먼저 한다. 큰 업로드에서 바이너리 판정 비용을 쓰기 전에 거절하기 위해서다.

## 비고
- 정하지 않은 것(스펙에 없음): 0바이트 빈 파일은 허용한다. 필요하면 후속 결정.
- 이 모듈은 경로 정리(`../` 등 경로 이탈 방지)를 하지 않는다. 저장 시점의 경로 안전성은 T067(file_storage)의 책임이다. `is_excluded_path`는 폴더 업로드의 제외 폴더 판정만 한다.
- 다음: T065(언어 감지, Pygments).
