# TASK-076. FileUpload 컴포넌트

## 상태
완료

## 날짜
2026-11-16

## 작업 요약
코드 파일을 올리는 **끌어다 놓기 + 파일 선택** 영역을 만들었다. 우체국 접수 창구처럼, 서류(파일)를 올려놓으면 직원이 규칙(확장자·크기·개수)을 먼저 확인하고, 문제가 있으면 접수하지 않고 이유를 알려준다. 클라이언트에서도 같은 규칙을 미리 검증하는 공용 모듈 `upload-validation.ts`도 이 태스크에서 함께 만들었다(T077~T081이 재사용).

| 항목 | 동작 |
|------|------|
| 입력 | 여러 파일 선택(`파일 선택`) 또는 `파일 끌어놓기 영역`에 drop |
| 누적 | 기존 목록에 이어서 추가, 이름·크기·수정시각이 같은 파일은 중복 제외 |
| 검증 | 확장자 12종, 파일당 10MB, 합계 10MB, 1~20개(FR-014~018). 실패하면 선택을 바꾸지 않고 `role="alert"`로 한국어 오류 표시, 이후 정상 추가하면 오류 해제 |
| 목록 | 파일명 + `{이름} 제거` 버튼 |
| 제어 | 상위가 `files`/`onChange`를 소유하는 controlled 컴포넌트, `disabled` 지원 |

오류 문구는 requirements-addendum의 좋은 예시("파일 업로드 실패: 파일 크기가 10MB를 초과합니다. ...")와 백엔드 `file_validator.py` 문구에 맞췄다.

## 변경 파일
- `frontend/src/components/upload/FileUpload.tsx` (신규)
- `frontend/src/lib/upload-validation.ts` (신규): 상수, `validateUploadFiles`, `isExcludedPath`, `validatePaste`, `validateTaskTitle`, `validateTaskDescription`
- `frontend/tests/unit/FileUpload.test.tsx` (신규): 9개
- `frontend/tests/unit/upload-validation.test.ts` (신규): 23개
- `frontend/tests/fixtures/files.ts` (신규): 크기를 속인 `File` 생성 헬퍼
- `docs/task-reports/TASK-076-FileUpload-컴포넌트.md` (신규)

## TDD 결과
- RED 커밋: 해당 없음(Git 저장소 아님). 구현 전 `Failed to resolve import "../../src/components/upload/FileUpload"`(및 `upload-validation`)로 테스트 파일이 실패하는 것을 확인했다.
- GREEN 커밋: 해당 없음. 구현 후 FileUpload 9개, upload-validation 23개 통과(중복 파일 케이스는 fixture의 `lastModified`가 호출마다 달라 실패해 fixture를 고정값으로 고침), 전체 360개 통과.
- REFACTOR 커밋: 해당 없음.
- 테스트 커버리지: `FileUpload.tsx` 문장 100%, 분기 88.9%(`disabled`일 때 drop 무시 등 방어 분기 미검증). `upload-validation.ts` 100%.

## 기술 결정
- **검증 실패 시 선택을 바꾸지 않음**: 잘못된 파일 하나 때문에 이미 고른 파일이 사라지지 않게 했다.
- **`accept` 속성을 쓰지 않음**: 쓰면 파일 선택창은 지원 확장자만 보여 주지만 drop에는 적용되지 않아 오류 경로가 둘로 갈린다. 선택·drop 모두 같은 검증과 같은 문구를 쓰도록 생략했다.
- **검증을 `upload-validation.ts`에 모음**: 백엔드와 같은 규칙을 한 곳에 두어 폴더·붙여넣기·모달이 공유한다.
- **바이너리 검사는 클라이언트에서 하지 않음**: 파일 내용을 읽어야 해서 비동기·복잡도가 늘고, 서버가 `binary_file` 오류로 막는다(FR-016). 서버 오류는 모달이 그대로 보여준다.

## 비고
- Git 저장소가 아니라 커밋은 없다.
