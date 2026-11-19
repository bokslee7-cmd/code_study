# TASK-018. React Router 라우트 구조

## 상태
완료

## 날짜
2026-11-02

## 작업 요약
`frontend/src/App.tsx`에 React Router v6 라우트 구조를 설정하고, `main.tsx`에서 `BrowserRouter`로 앱을 감쌌다.

| 경로 | 화면 | 비고 |
|------|------|------|
| `/` | `/dashboard`로 리다이렉트 | `replace` 이동 |
| `/login` | 로그인 | 임시 화면 (T036에서 교체) |
| `/register` | 회원가입 | 임시 화면 (T035에서 교체) |
| `/dashboard` | 대시보드 | 임시 화면 (T054에서 교체) |
| `/projects/:projectId` | 프로젝트 상세 | 임시 화면 (T055에서 교체) |
| `/projects/:projectId/tasks/:taskId` | 태스크 상세 | 임시 화면 (T083에서 교체) |
| `/trash` | 휴지통 | 임시 화면 (T181에서 교체) |
| `*` | 404 안내 + 대시보드 링크 | 정의되지 않은 모든 경로 |

## 변경 파일
- frontend/src/App.tsx (라우트 정의, 임시 화면 컴포넌트, 404 화면)
- frontend/src/main.tsx (`BrowserRouter` 추가)
- frontend/tests/unit/App.test.tsx (기존 제목 테스트를 라우팅 테스트 10개로 교체)
- specs/001-ai-code-learning-platform/tasks.md (T018 체크)

## TDD 결과
- RED 커밋: 해당 없음 (Git 저장소 아님). 테스트 10개 전부 실패 확인.
- GREEN 커밋: 해당 없음. 구현 후 10개 통과.
- REFACTOR 커밋: 해당 없음. 별도 리팩터링 없음.
- 테스트 커버리지: `App.tsx` 100% (Stmts/Branch/Funcs/Lines). tsc, eslint, prettier 통과.

## 기술 결정
- **`BrowserRouter`는 `App`이 아닌 `main.tsx`에 둠**: 테스트에서 `MemoryRouter`로 경로를 지정해 렌더링할 수 있게 하기 위해서다.
- **각 페이지는 임시 화면으로 연결**: 실제 페이지는 후속 Task(T035, T036, T054, T055, T083, T181)의 범위다. 해당 Task에서 `element`만 교체하면 된다.
- **기존 "AI 코드 학습 플랫폼" 제목 화면 제거**: `/`가 대시보드로 이동하므로 루트 화면이 없어졌다. 앱 제목은 레이아웃/네비게이션을 만들 때 다시 넣는다.
- **`/projects/:projectId/unknown` 같은 하위 경로는 404**: 정의된 경로만 허용한다.

## 비고
- 로그인 필요 경로 보호(`ProtectedRoute`)는 T037의 범위라 포함하지 않았다. T037에서 보호 대상 경로를 감싸야 한다.
- 테스트 실행 시 React Router v7 대비 future flag 경고가 출력된다. 동작에는 영향이 없다.
- Git 저장소가 아니라 커밋은 없다.
- 선행 확인: T017(Celery·Redis)은 아직 미완료이지만, T018은 프론트엔드 작업이라 의존성이 없다.
