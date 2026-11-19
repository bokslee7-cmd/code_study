# TASK-066. 코드 복잡도 분석기 (complexity_analyzer)

## 상태
완료

## 날짜
2026-11-16

## 작업 요약
업로드된 코드의 난이도(`beginner` / `intermediate` / `advanced`, FR-021)를 판정하는 순수 함수 모음을 만들었다. 결과는 `uploaded_code.complexity_level`에 저장되며, 값은 DB 체크 제약과 동일하다.

세 지표 중 가장 높은 수준을 채택한다.

| 지표 | 중급 | 고급 |
|------|------|------|
| 코드 줄 수(빈 줄·주석·text/markdown 제외) | 80 초과 | 300 초과 |
| 함수 개수 | 5 초과 | 15 초과 |
| 최대 중첩 깊이 | 4 이상 | 6 이상 |

| 함수 | 역할 |
|------|------|
| `analyze_complexity(files)` | `(파일명, 내용)` 목록 → `ComplexityResult(level, total_lines, code_lines, function_count, max_nesting_depth)` |
| `count_functions(content, language)` | 언어별 함수/메서드 정의 수 |
| `max_nesting_depth(content, language)` | Python은 들여쓰기, C 계열은 중괄호 깊이 |

`total_lines`는 `uploaded_code.total_lines`에 넣을 값(빈 줄·주석 포함 전체 줄 수)이다. 언어는 T065 `detect_language`로 판별한다.

## 변경 파일
- `backend/src/services/code_analysis/complexity_analyzer.py` (신규)
- `backend/tests/unit/test_complexity_analyzer.py` (신규, 30개 테스트)
- `specs/001-ai-code-learning-platform/tasks.md` (T066 완료 표시)

## TDD 결과
- RED: 구현 전 테스트 작성(모듈 부재). 별도 실패 실행은 생략하고 구현 후 바로 실행함
- GREEN: 1차 실행에서 30/30 통과
- REFACTOR: black 적용, ruff 긴 줄 1건 수정, mypy 통과
- 커버리지: `complexity_analyzer.py` 100%
- 전체 백엔드: 608 passed, 43 skipped
- 커밋: Git 저장소가 아니라 없음

## 기술 결정
- 임계값은 스펙에 없어 직접 정한 값이다(초보자 대상 학습 플랫폼 기준의 경험적 값). 상수로 분리해 한 곳에서 조정할 수 있다.
- 지표별 최댓값 방식을 택했다. 줄 수가 적어도 중첩이 깊거나 함수가 많으면 초보자에게는 어렵기 때문이다.
- 주석·빈 줄은 줄 수에서 뺀다. 공백으로 난이도가 올라가는 것을 막기 위해서다. `text`/`markdown` 파일은 코드가 아니므로 줄 수·함수 수에 넣지 않는다(`total_lines`에는 포함).
- 중괄호 깊이는 문자열·주석을 먼저 제거한 뒤 센다. `"{{{"` 같은 문자열이 깊이를 부풀리지 않는다. 닫는 괄호가 많아도 깊이는 0 밑으로 내려가지 않는다.
- C 계열(Java/C/C++) 함수 탐지는 `타입 이름(...) {` 정규식이며 `if/for/while/switch/catch` 등은 이름 필터로 제외한다. JS/TS는 `function` 키워드와 `=>` 개수를 센다.
- 파서(AST)를 쓰지 않았다. 다언어 지원과 단순함을 위한 선택이며, 정확도보다 대략적 등급 판정이 목적이다.

## 비고
- 한계: Java는 클래스 한 겹이 항상 깊이에 더해져 같은 구조의 Python보다 깊이가 1 크게 나온다. JS 클래스 메서드 축약형(`foo() {}`)과 멀티라인 템플릿 문자열 안의 코드는 함수로 세지 못할 수 있다. 정밀도가 문제되면 후속 개선.
- HTML/CSS는 줄 수만 반영되고 깊이·함수는 0이다.
- 이 서비스는 아직 어디서도 호출되지 않는다. T069(CodeUploadService)에서 `detect_dominant_language`와 함께 연결한다.
- 다음: T067(파일 저장 서비스).
