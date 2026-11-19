# TASK-099. Monaco Editor 설치·설정

## 상태
완료

## 날짜
2026-11-18

## 작업 요약
코드를 읽기 전용으로 보여 줄 Monaco Editor를 프론트엔드에 연결했다. `@monaco-editor/react`는 이미 `frontend/package.json`에 있어 새로 설치한 패키지는 없다. 테스트(jsdom)에서 Monaco를 바꿔 끼울 수 있도록 Monaco는 `CodeEditor` 한 곳에서만 import한다.

- `lib/monaco-config.ts`: 읽기 전용 옵션(`MONACO_OPTIONS`: readOnly, domReadOnly, 줄 바꿈, 미니맵 끔, automaticLayout)과 서버 언어 이름을 Monaco 언어 id로 바꾸는 `toMonacoLanguage`(js/ts/py/c++/c# 별칭, 빈 값은 `plaintext`).
- `components/document/CodeEditor.tsx`: Monaco 래퍼. 값·언어·경로를 넘기고, `highlightLine`이 있으면 그 줄을 강조(`document-highlight-line`)하고 가운데로 스크롤하며, 스크롤하면 화면 맨 위 줄 번호를 `onTopLineChange`로 알린다. 강조 때문에 일어난 프로그램 스크롤은 300ms 동안 알림에서 제외한다(코드 스크롤 ↔ 설명 동기화가 서로 되돌려 보내지 않게 하려는 것).
- `index.css`: 강조 줄 배경색 클래스 추가.
- `types/document.ts`: 문서 관련 타입(CHAPTER_SCHEMA를 TypeScript로 옮김). T100~T108이 함께 쓴다.

## 변경 파일
- `frontend/src/lib/monaco-config.ts` (신규)
- `frontend/src/components/document/CodeEditor.tsx` (신규)
- `frontend/src/types/document.ts` (신규)
- `frontend/src/index.css` (강조 줄 스타일 추가)
- `frontend/tests/unit/monaco-config.test.ts` (신규): 9개
- `frontend/tests/unit/CodeEditor.test.tsx` (신규): 6개. `@monaco-editor/react`를 모킹한다.
- `docs/task-reports/TASK-099-Monaco-Editor-설정.md` (신규)

## TDD 결과
- RED: Git 저장소가 아니라 커밋은 없다. 구현 전 실행해 두 테스트 파일이 import 해석 실패로 실패하는 것을 확인했다.
- GREEN: 구현 후 15개 통과, `tsc -b` 오류 없음.
- REFACTOR: 없음.

## 기술 결정
- **Monaco는 CDN 로더 그대로 사용**: `@monaco-editor/react` 기본 동작(jsDelivr에서 Monaco 로드)을 따랐다. 번들에 직접 포함하는 설정은 하지 않았다.
- **Monaco의 `Range` 대신 평범한 객체 사용**: 강조 줄 범위를 `{startLineNumber, ...}` 객체로 넘겨 `monaco` 인스턴스를 들고 다니지 않게 했다.

## 비고
- 실제 브라우저에서 Monaco가 로드되는 것(CDN 접속 포함)은 이번 범위에서 확인하지 않았다. 테스트는 모킹한 편집기로만 동작을 확인했다.
- 오프라인 환경이나 CSP가 CDN을 막는 환경에서는 편집기가 뜨지 않을 수 있다.
