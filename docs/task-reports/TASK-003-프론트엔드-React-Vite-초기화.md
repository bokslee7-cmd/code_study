# TASK-003. 프론트엔드 React(Vite + TypeScript) 프로젝트 초기화

## 상태
완료

## 날짜
2026-10-29

## 작업 요약
`frontend/`에 Vite + React 18 + TypeScript 프로젝트를 구성했다.
- 런타임 의존성(quickstart.md 기준): react, react-dom, react-router-dom, @tanstack/react-query, zustand, @monaco-editor/react, axios
- 개발 의존성: vite, @vitejs/plugin-react, typescript(strict), vitest, @vitest/coverage-v8, jsdom, @testing-library/react·jest-dom·user-event
- 스크립트: `dev`, `build`, `preview`, `test`, `test:watch`, `test:coverage`
- 최소 `App` 컴포넌트(제목 렌더링)와 `main.tsx` 진입점

## 변경 파일
- frontend/package.json, package-lock.json (신규)
- frontend/tsconfig.json, vite.config.ts, index.html (신규)
- frontend/src/main.tsx, App.tsx, vite-env.d.ts, test/setup.ts (신규)
- frontend/tests/unit/App.test.tsx (신규)

## TDD 결과
- RED 커밋: 해당 없음 (Git 저장소가 아니라 커밋 없음). `App.tsx` 없이 테스트를 실행해 import 해석 실패로 FAIL 확인.
- GREEN 커밋: 해당 없음. `App.tsx` 작성 후 1개 테스트 PASS.
- REFACTOR 커밋: 해당 없음 (리팩터링 대상 없음)
- 테스트 커버리지: 100% (App.tsx)

추가 검증: `tsc -b` 타입 오류 없음, `vite build` 성공(번들 142KB, gzip 46KB).

## 기술 결정
- **React 18 / Vite 5 / Vitest 1 유지**: quickstart.md의 버전 범위를 따랐다. 최신 메이저(React 19, Vite 6+)로 올리지 않았다.
- **테스트 위치**: `frontend/tests/unit/`에 둔다(plan.md 구조). vite.config.ts의 `include`에 `src/**`와 `tests/**`를 모두 넣어 co-located 테스트도 허용한다.
- **범위 한정**: Tailwind·shadcn(T022), ESLint·Prettier(T006), Router 구성(T018), Query 클라이언트(T019), axios 설정(T020), Zustand 스토어(T021)는 해당 태스크에서 한다. 이번에는 패키지만 설치했다.

## 비고
- `tsconfig.tsbuildinfo`, `dist/`, `coverage/` 같은 빌드 산출물은 삭제했다. `.gitignore`는 T007에서 만든다.
- 설치 시 `esbuild` postinstall 스크립트 경고가 나왔으나 빌드·테스트는 정상 동작했다.
- `@testing-library/jest-dom`이 v7로 설치되었다. 현재 설정(`@testing-library/jest-dom/vitest`)에서 정상 동작을 확인했다.
- 다음 작업: T004(Docker Compose), T005~T007은 병렬 가능.
