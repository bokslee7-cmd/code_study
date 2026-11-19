# TASK-077. FolderUpload 컴포넌트

## 상태
완료

## 날짜
2026-11-16

## 작업 요약
폴더를 통째로 고르는 업로드 영역을 만들었다. 이삿짐을 상자(폴더)째 받되, 쓰레기(`.git`, `node_modules`, `__pycache__`, `.DS_Store`)는 현관에서 빼고 몇 개를 뺐는지 알려주는 것과 같다.

| 항목 | 동작 |
|------|------|
| 입력 | `폴더 선택`(`webkitdirectory` + `multiple`) |
| 구조 보존 | 목록에 `File.webkitRelativePath`(예: `todo/lib/util.py`)를 그대로 표시, 전송 시에도 이 경로를 사용 |
| 자동 제외 | 경로에 `.git`/`node_modules`/`__pycache__` 폴더 또는 `.DS_Store` 파일이 있으면 제외하고 `role="status"`로 `N개 항목은 자동으로 제외했습니다.` 표시 |
| 검증 | 제외 후 남은 파일에 `validateUploadFiles` 적용(확장자·10MB·합계·1~20개). 실패하면 선택을 바꾸지 않고 `role="alert"` |
| 재선택 | 다시 고르면 이전 선택을 대체, `선택 지우기`로 비움 |

## 변경 파일
- `frontend/src/components/upload/FolderUpload.tsx` (신규)
- `frontend/tests/unit/FolderUpload.test.tsx` (신규): 8개
- `docs/task-reports/TASK-077-FolderUpload-컴포넌트.md` (신규)

## TDD 결과
- RED 커밋: 해당 없음(Git 저장소 아님). 구현 전 `Failed to resolve import "../../src/components/upload/FolderUpload"`로 실패하는 것을 확인했다.
- GREEN 커밋: 해당 없음. 구현 후 8개 통과. 첫 실행에서 `multiple` 속성이 없어 userEvent가 여러 파일을 올리지 못한 케이스가 실패해 `multiple`을 추가했다(브라우저에서는 `webkitdirectory`가 다중 선택을 뜻하므로 무해).
- REFACTOR 커밋: 해당 없음.
- 테스트 커버리지: `FolderUpload.tsx` 문장·함수 100%, 분기 90.9%.

## 기술 결정
- **지원하지 않는 확장자가 섞인 폴더는 거부**: 이미지 등을 조용히 건너뛰면 사용자가 올린 줄 아는 코드와 서버에 간 코드가 달라진다. 백엔드(`validate_upload`)와 같은 동작이며 오류에 파일명이 나온다. 폴더에 비코드 파일이 흔하다는 사용성 문제는 브라우저 수동 테스트(T085)에서 재평가할 대상이다.
- **`webkitdirectory`는 스프레드로 부여**: React 타입에 없는 비표준 속성이라 `{...{ webkitdirectory: '' }}`로 넘긴다.

## 비고
- Git 저장소가 아니라 커밋은 없다.
