# TASK-093. DocumentGenerationService (재시도 로직)

## 상태
완료

## 날짜
2026-11-18

## 작업 요약
`backend/src/services/document/document_generation_service.py`에 7챕터 학습 문서를 만드는 서비스를 구현했다. `GeminiClient`(T091)로 `build_document_prompt`(T092)의 프롬프트를 보내고, 응답에서 JSON을 꺼내 챕터별로 검증하고, 실패하면 재시도한다. `generate(files, ...)`는 DB를 쓰지 않는 순수 로직이다. 이후 요청으로 `generate_document(task_id)`를 추가해 DB 저장까지 맡긴다(아래 "추가 작업").

- `DocumentGenerationService(client).generate(files, language=, complexity_level=None)` → `GenerationResult(content, failed_chapters, attempts)`. `content`는 항상 `chapter1`~`chapter7` 키를 가진다(DB의 `valid_content_structure` 제약 충족).
- `parse_json_object(text)`: 앞뒤 잡담·코드 펜스를 무시하고 첫 JSON 객체를 꺼낸다. 중간에 끊긴 응답은 열린 문자열·괄호를 닫아 복구한다(CHK013).
- 재시도 예산은 두 개이고 서로 독립이다.
  - API 문제(재시도 가능한 오류, 빈 응답): 최대 3회, 대기 `min(60, 2×2^n + 지터(0~1초))`초 = 2·4·8초(FR-090, CHK007).
  - 내용 문제(JSON 아님, 챕터 검증 실패): 최대 2회. 재시도 프롬프트에 문제점을 넣고 temperature를 0.7→0.8로 올린다(CHK006).
- 재시도가 끝났는데도 챕터가 틀리면 가장 많이 맞은 시도를 쓴다. 유효한 챕터가 5개 이상이면 부분 수용하고, 틀린 챕터는 `{"generation_failed": true}`로 채운다. 5개 미만이면 `DocumentGenerationError`.
- 재시도가 불가능한 오류(키 없음, 4xx 등)는 즉시 `DocumentGenerationError`로 바꿔 던진다(`__cause__`에 원본).

## 추가 작업: generate_document(task_id) (2026-11-18)
수동 테스트 요청(태스크 코드 → 문서 생성 → 상태·저장·404 확인)에 맞춰 서비스에 `generate_document(task_id)`를 추가했다. 생성자는 `DocumentGenerationService(client, session)`.

- 활성 태스크를 찾고(없거나 휴지통이면 `NotFoundException` 404, `details={"task_id"}`, 한글 메시지·제안 포함), `CodeUploadService.get_code`로 코드를 읽는다(코드가 없으면 404).
- `LearningDocument` 행이 없으면 만들고(빈 챕터 7개 뼈대), 있으면 재사용해 `in_progress`로 바꾼 뒤 **commit**한다. 폴링하는 쪽(T098)이 생성 도중에도 상태를 볼 수 있게 하려는 것이라, 다른 서비스와 달리 이 메서드는 직접 commit한다.
- 성공 → `completed` + content 저장. 부분 수용이면 `generation_error`에 "일부 챕터를 만들지 못했습니다: chapterN"을 남긴다. 실패 → `failed` + 사유(최대 2000자) 저장 후 예외를 다시 던진다.
- 언어·복잡도는 `UploadedCode`의 값을 쓴다.
- 이미 `in_progress`인 문서의 동시 실행 방지는 하지 않는다(T095 큐의 몫).

### 수동 테스트 결과 (실제 DB + 실제 Gemini, 임시 DB는 끝나고 삭제)
- 29줄 파이썬(점수 관리 프로그램)으로 user/project/task/uploaded_code/code_file 생성. 별도 DB 연결로 관찰한 상태: `in_progress -> completed`, 28.2초, `generation_error=None`.
- 저장된 content 길이(JSON 글자수): chapter1 125 / chapter2 943(개념 5) / chapter3 533 / chapter4 5528(설명 19줄) / chapter5 890(단계 5) / chapter6 659(개념 3) / chapter7 914(실수 3). 7개 모두 저장. 챕터 4의 줄 번호 19개는 코드의 비어 있지 않고 주석이 아닌 줄과 일치.
- 없는 task_id: `NotFoundException`, status 404, error `not_found`, 메시지 "학습 문서를 만들 태스크를 찾을 수 없습니다. 삭제되었거나 존재하지 않는 태스크입니다.", 제안 "태스크 목록에서 태스크가 남아 있는지 확인한 뒤 다시 시도하세요."

## 변경 파일
- `backend/src/services/document/__init__.py` (신규, 빈 파일)
- `backend/src/services/document/document_generation_service.py` (신규)
- `backend/tests/unit/test_document_generation_service.py` (신규, 37개)
- `backend/tests/integration/test_document_generation_integration.py` (신규, 7개, 실제 PostgreSQL 필요)
- `specs/001-ai-code-learning-platform/tasks.md` (T093 완료 표시)

## TDD 결과
- RED: 모듈이 없어 테스트 수집 단계에서 실패하는 것을 확인했다.
- GREEN: 37개 통과, 서비스 커버리지 99%(미커버 1줄은 `parse_json_object`의 "최상위가 객체가 아님" 분기 — 대괄호만 있는 입력은 앞 단계에서 걸러져 도달하지 않는다). 백엔드 전체 824개 통과(52개는 DB가 꺼져 있어 skip). `generate_document` 추가 후 통합 테스트 7개를 더해 DB를 켠 상태로 883개 통과, 커버리지 99%, ruff·black·mypy(strict) 이상 없음.
- 실제 API 확인: 5줄짜리 파이썬 코드로 `gemini-3-flash-preview`를 한 번 호출했다. 1회 시도에 7챕터가 모두 검증을 통과했고(`failed_chapters=()`), 챕터 4의 줄 번호는 `[1, 2, 4, 5]`로 코드의 비어 있지 않은 줄과 일치했다. 재시도·부분 수용 경로는 가짜 클라이언트 테스트로만 확인했고 실제 API로는 보지 못했다.
- 커밋 해시: 없음(git 저장소가 아님).

## 기술 결정
- **검증 기준은 실제 스키마(`CHAPTER_SCHEMA`)를 따랐다.** requirements-addendum CHK005는 옛 챕터 구성(title/content/key_points, 연습문제)을 전제로 하고 있어 그대로 쓸 수 없었다. 챕터마다 필수 문자열 필드가 비어 있지 않은지, 목록이 비어 있지 않은지, `line_number`가 1 이상의 정수인지를 검사한다. 챕터 2 개념 5개 이하, 챕터 7 실수 3~5개 같은 개수 한도는 검사하지 않는다(프롬프트로만 요청).
- **금지 패턴:** `[TODO]`·`[GENERATE]` 자리표시와 `<script>`·`<iframe>` 등 위험 태그가 있으면 그 챕터를 무효로 본다. 코드를 담는 필드(`code`, `example`, `wrong_code`, `right_code`, `alternatives`, `flowchart`, `syntax_breakdown`)는 HTML 코드를 설명하는 문서가 있을 수 있어 태그 검사에서 뺐다. 프런트는 어차피 텍스트로 렌더링해야 한다.
- **temperature 0.7(첫 시도)→0.8(내용 재시도)**은 addendum을 따랐다. FR-039(같은 코드는 같은 구조)와 긴장이 있으므로, 같은 구조가 더 중요하면 `RETRY_TEMPERATURE`를 0.7로 낮추면 된다.
- **부분 수용은 한 시도 안에서 고른다.** 여러 시도의 유효 챕터를 섞지 않는다. 시도마다 챕터 간 일관성이 다를 수 있어서다.
- `sleep`과 `jitter`를 생성자에서 주입받아 테스트에서 실제로 기다리지 않는다.
- `GeminiEmptyResponseError`는 `retryable=False`이지만 addendum(CHK013 "빈 응답은 즉시 재시도")에 따라 API 예산으로 재시도한다.

## 비고
- **미구현:** CHK006의 마지막 수단인 "기본 템플릿 생성"(코드에서 함수·클래스를 뽑아 최소 설명을 만드는 것). 지금은 5챕터 미만이면 실패로 끝난다. 필요하면 별도 Task로 분리해야 한다.
- **미구현:** 챕터 4의 `line_number`가 실제 코드 줄과 맞는지, 챕터마다 비유가 있는지(CHK005 키워드 검사)는 검사하지 않는다. 비유 키워드는 영어 기준이라 한국어 응답에는 맞지 않는다.
- **시간 제한:** 호출 한 번의 제한은 180초(T091)지만, 재시도를 모두 쓰면 최악의 경우 총 6회 호출 + 대기 14초가 된다. FR-025(3분)의 전체 제한은 이 서비스가 아니라 T094의 Celery 타임아웃에서 걸어야 한다.
- **대용량 코드:** T092 비고의 분할 생성 문제는 아직 열려 있다. 실측은 5~9줄짜리 코드뿐이고, 500줄 코드에서 출력이 토큰 한도에 걸리면 `GeminiEmptyResponseError` 또는 끊긴 JSON(복구 후 일부 챕터 무효)으로 나타난다. 대용량 실측 후 T094 전에 판단하는 것이 좋다.
- T094에서는 `GenerationResult.failed_chapters`가 비어 있지 않으면 경고 배너용 정보로 저장하고, `DocumentGenerationError.problems`는 `generation_error` 컬럼에 기록하면 된다.
