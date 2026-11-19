# TASK-065. 언어 감지 서비스 (language_detector)

## 상태
완료

## 날짜
2026-11-16

## 작업 요약
업로드된 코드(파일 또는 붙여넣기)가 어떤 언어인지 판별하는 순수 함수 모음을 만들었다. 결과는 `uploaded_code.detected_language`에 저장될 정규화된 이름(`python`, `javascript`, `typescript`, `html`, `css`, `java`, `cpp`, `c`, `markdown`, `text`)이다.

판별 순서: 확장자 → shebang → 내용 패턴(정규식) → Pygments `guess_lexer` → `text`.

| 함수 | 역할 |
|------|------|
| `get_language_for_extension` | 확장자(점 포함, 대소문자 무시) → 언어, 모르면 `None` |
| `detect_language(content, file_name=None)` | 파일 1개/붙여넣기 코드의 언어. 항상 문자열 반환 |
| `detect_dominant_language(files)` | `(파일명, 내용)` 목록에서 줄 수가 가장 많은 언어. 파일 없으면 `None` |
| `get_lexer_alias` | 구문 강조용 Pygments alias. 모르는 언어는 `text` |

## 변경 파일
- `backend/src/services/code_analysis/language_detector.py` (신규)
- `backend/src/services/code_analysis/__init__.py` (신규, 빈 패키지 파일)
- `backend/tests/unit/test_language_detector.py` (신규, 45개 테스트)
- `specs/001-ai-code-learning-platform/tasks.md` (T065 완료 표시)

## TDD 결과
- RED: 모듈 부재로 수집 단계 실패 확인
- GREEN: 1차 구현에서 39/39 통과
- REFACTOR: ruff 통과(긴 줄 정리), black 통과, mypy 통과
- 커버리지: `language_detector.py` 100% (경계 케이스 6개 추가 후)
- 전체 백엔드: 577 passed, 43 skipped (추가 테스트 전 기준. 마지막 shebang 테스트 1개는 해당 파일만 실행해 45 passed 확인)
- 커밋: Git 저장소가 아니라 없음

## 기술 결정
- 확장자가 1순위다. research.md의 "확장자 매핑이 주된 방법" 결정을 따랐다. `.h`는 research.md의 Phase 1 목록에 있어 `c`로 매핑했다(업로드 화이트리스트에는 없음).
- Pygments `guess_lexer`만으로는 부족했다. 사전 실험에서 Java 스니펫은 `Text only`, JavaScript 스니펫은 `GDScript`로 나왔다. 그래서 Java/JS/Python/C/C++/HTML/CSS는 정규식 패턴을 먼저 적용하고, Pygments는 그다음 보조로만 쓴다. Pygments 결과도 지원 언어 목록에 있는 것만 채택한다.
- 패턴 순서가 중요하다. 구체적인 것(html, java, cpp)을 앞에 두고 흔한 것(javascript의 `=>`, `function`)을 뒤에 둬 오탐을 줄였다.
- `detect_dominant_language`는 `text`/`markdown`을 코드 언어가 하나라도 있으면 제외한다. README.md 줄 수가 많아도 프로젝트 언어가 `markdown`이 되지 않게 하기 위해서다. 동률은 언어 이름 알파벳순으로 정해 결과가 항상 같다.
- 확장자 추출은 파일명 안에서 직접 한다(`.bashrc`, `trailing.`은 확장자 없음). `file_validator.get_extension`과 규칙이 같지만 서비스 → 유틸 의존을 늘리지 않으려고 작은 중복을 택했다.

## 비고
- 내용 패턴은 휴리스틱이다. 확장자가 없는 짧은 붙여넣기 코드는 `text`로 나오거나 오판할 수 있다. 붙여넣기 UI(T076~)에서 사용자가 언어를 직접 고르게 하는 것이 정확하다. T086(수동 브라우저 테스트)에서 실제 붙여넣기 코드로 확인 필요.
- `.jsx`는 `javascript`, `.tsx`는 `typescript`로 합쳤다. JSX/TSX를 따로 구분해야 하면 후속 결정.
- 전체 테스트 수가 이전 보고(576)와 단순 비교되지 않는다. 이전 보고는 통과 수만 적었고, 이번에는 skipped 43개(DB 필요 테스트로 추정, 미확인)가 따로 집계된다.
- 다음: T066(복잡도 분석기).
