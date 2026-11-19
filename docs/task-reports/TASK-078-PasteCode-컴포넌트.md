# TASK-078. PasteCode 컴포넌트

## 상태
완료

## 날짜
2026-11-16

## 작업 요약
코드를 직접 붙여넣는 **언어 선택 + 코드 입력창**을 만들었다. 편지를 보낼 때 받는 사람 주소(언어)와 내용(코드)을 같이 적는 양식이다.

| 항목 | 동작 |
|------|------|
| 언어 | 라벨 `프로그래밍 언어`, 첫 옵션 `언어 선택`(빈 값), 이어서 Python·JavaScript·TypeScript·HTML·CSS·Java·C++·C 8종 |
| 코드 | 라벨 `코드`, 고정폭 글꼴 textarea |
| 제어 | `value`(`{code, language}`)/`onChange`로 상위가 상태를 소유, `error`가 있으면 `role="alert"`, `disabled` 지원 |

언어 값(`python`, `javascript`, `typescript`, `html`, `css`, `java`, `cpp`, `c`)은 백엔드 `PASTE_LANGUAGES` 키와 같다. 검증(`validatePaste`: 코드 비어 있음 / 언어 미선택 / 10MB 초과)은 TASK-076의 `upload-validation.ts`에 있고 모달이 호출한다.

## 변경 파일
- `frontend/src/components/upload/PasteCode.tsx` (신규)
- `frontend/tests/unit/PasteCode.test.tsx` (신규): 7개
- `docs/task-reports/TASK-078-PasteCode-컴포넌트.md` (신규)

## TDD 결과
- RED 커밋: 해당 없음(Git 저장소 아님). 구현 전 `Failed to resolve import "../../src/components/upload/PasteCode"`로 실패하는 것을 확인했다.
- GREEN 커밋: 해당 없음. 구현 후 7개 통과.
- REFACTOR 커밋: 해당 없음.
- 테스트 커버리지: `PasteCode.tsx` 문장·분기·함수 100%.

## 기술 결정
- **네이티브 `<select>` 사용**: 프로젝트에 Select UI 컴포넌트가 없고, 8개 옵션에는 네이티브가 접근성·모바일 모두 충분하다.
- **백엔드가 지원하는 `text`/`markdown`은 목록에서 뺌**: 요구사항(FR-013)이 프로그래밍 언어 선택이므로 코드 언어 8종만 노출했다.

## 비고
- 서버가 언어 미지정 시 주는 문구("코드 언어를 선택하세요.")와 클라이언트 문구("프로그래밍 언어를 선택하세요.")가 약간 다르다. 클라이언트가 먼저 막으므로 사용자에게는 클라이언트 문구가 보인다.
- Git 저장소가 아니라 커밋은 없다.
