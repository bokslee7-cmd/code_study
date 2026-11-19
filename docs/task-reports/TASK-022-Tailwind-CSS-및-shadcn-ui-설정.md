# TASK-022. Tailwind CSS 및 shadcn/ui 설정

## 상태
완료

## 날짜
2026-11-04

## 작업 요약
프론트엔드에 스타일링 도구인 Tailwind CSS(v4)를 붙이고, 미리 만들어진 화면 부품 모음인 shadcn/ui를 설치했다. 이제 `className="flex gap-2"`처럼 짧은 이름만 적어도 스타일이 적용되고, 버튼·입력창·카드는 직접 만들지 않고 가져다 쓸 수 있다.

| 구성 | 내용 |
|------|------|
| Tailwind CSS | v4.3.4 + `@tailwindcss/vite` 플러그인. `src/index.css`의 `@import "tailwindcss"`로 켠다 |
| 테마 | shadcn 기본(Nova, neutral) 색상 변수를 라이트/다크 모두 `src/index.css`에 정의 |
| 경로 별칭 | `@/` = `src/` (`vite.config.ts`, `tsconfig.json` 양쪽) |
| shadcn 설정 | `components.json` (radix 기반, lucide 아이콘) |
| 설치한 컴포넌트 | `button`, `input`, `label`, `card` — 인증 화면(T032~T036)에서 바로 쓸 것들 |
| 유틸 | `cn()` — 클래스 이름을 합치고 충돌(`p-2`, `p-4`)이 나면 뒤엣것을 남긴다 |

비유하면 Tailwind는 "색연필 세트", shadcn/ui는 "조립식 부품 상자"다. 색연필(작은 스타일 이름)을 조합해 칠하고, 자주 쓰는 부품(버튼, 입력창)은 상자에서 꺼내 쓴다. 부품은 라이브러리를 통째로 빌려 오는 것이 아니라 소스 파일이 `src/components/ui/`에 복사되므로 우리 프로젝트에서 자유롭게 고칠 수 있다.

### 추가 작업: `/dev-test`에서 Tailwind·shadcn 동작 확인
기존 `/dev-test` 페이지에 `TailwindTest` 영역을 붙여 세 가지를 눈으로 확인할 수 있게 했다.

| 섹션 | 내용 |
|------|------|
| Tailwind 클래스 테스트 | `bg-blue-500 text-white p-3 rounded-lg`를 적용한 샘플 박스와, 각 클래스가 하는 일의 텍스트 설명 |
| shadcn/ui 버튼 테스트 | `default`, `outline`, `ghost` 버튼 3개. 누르면 variant 이름을 `alert`로 표시 |
| 반응형 디자인 테스트 | 카드 3개 그리드. 모바일 1열, `md`(768px) 이상 2열, `lg`(1024px) 이상 3열 |

`rounded-lg`는 Tailwind 기본값(0.5rem)이 아니라 shadcn 테마의 `--radius`(0.625rem, 약 10px)를 따른다. 설명 문구도 이 값으로 적었다.

## 변경 파일
- `frontend/src/components/dev/TailwindTest.tsx` (신규): 위 세 섹션
- `frontend/tests/unit/TailwindTest.test.tsx` (신규): 클래스 적용, 설명 문구, 버튼 3개와 alert 호출, 그리드 열 수 클래스, 라우트 노출 테스트 14개
- `frontend/src/pages/DevTestPage.tsx`: `<TailwindTest />` 추가
- `frontend/package.json`: `tailwindcss`, `@tailwindcss/vite`, `radix-ui`, `class-variance-authority`, `cn`, `lucide-react`, `tw-animate-css`, `shadcn`, `@fontsource-variable/geist` 추가, 개발용 `@types/node` 추가
- `frontend/vite.config.ts`: Tailwind 플러그인, `@` 별칭 추가
- `frontend/tsconfig.json`: `paths`(`@/*`), `types`에 `node` 추가
- `frontend/eslint.config.js`: `src/components/ui/**`에서 `react-refresh/only-export-components` 해제
- `frontend/components.json` (신규): shadcn 설정
- `frontend/src/index.css` (신규): Tailwind 불러오기 + 테마 변수
- `frontend/src/main.tsx`: `./index.css` 불러오기
- `frontend/src/lib/utils.ts` (신규): `cn`
- `frontend/src/components/ui/{button,input,label,card}.tsx` (신규): shadcn 컴포넌트
- `frontend/src/components/dev/AuthStoreTest.tsx`: 개발 페이지 버튼 2개를 shadcn `Button`으로 교체 (화면에서 스타일 적용 확인용)
- `frontend/tests/unit/{utils.test.ts, ui-components.test.tsx, tailwind-setup.test.ts}` (신규): 테스트 21개
- `specs/001-ai-code-learning-platform/tasks.md`: T022 완료 표시
- `docs/task-reports/TASK-022-Tailwind-CSS-및-shadcn-ui-설정.md` (신규): 작업 결과 기록

## TDD 결과
- RED 커밋: 해당 없음 (Git 저장소 아님). 구현 전 테스트 3개 파일이 `components.json`, `@/lib/utils`, `@/components/ui/button` 부재로 실패하는 것을 확인했다.
- GREEN 커밋: 해당 없음. 구현 후 20개 통과 (카드 하위 영역 테스트 1개 추가). `/dev-test` 확인 영역은 구현 전에 컴포넌트 부재로 실패하는 것을 확인한 뒤 14개 통과. 프론트엔드 전체 99개 통과.
- REFACTOR 커밋: 해당 없음. 생성된 파일을 프로젝트 Prettier 스타일에 맞추고, `@types/node` 추가로 tsc 오류를 풀고, 카드 미사용 영역 테스트를 보강했다.
- 테스트 커버리지: 전체 100% (Stmts/Branch/Funcs/Lines). tsc, eslint, prettier 통과. `npm run build` 성공, 빌드된 CSS에 `.flex`, `.bg-primary`, `.rounded-lg`가 들어 있음을 확인했다.

## 기술 결정
- **Tailwind v3가 아닌 v4 사용**: quickstart.md의 `^3.3.0`은 예시 버전 표기였고, 현재 shadcn CLI(4.x)는 v4를 기준으로 한다. `@tailwindcss/vite`가 프로젝트의 Vite 5를 지원하는 것도 확인했다. v3로 맞추려면 별도 설정 파일(`tailwind.config`, PostCSS)이 필요하고 CLI 지원이 불확실해 v4를 택했다.
- **shadcn CLI로 설치, 베이스는 radix·프리셋은 Nova**: CLI 기본값을 따랐다. 프리셋에 따라 색과 모서리 둥글기만 다르므로 나중에 바꿔도 컴포넌트 사용 코드는 그대로다.
- **`cn`은 shadcn-ui 조직의 `cn` 패키지**: 기존 `clsx` + `tailwind-merge` 조합을 하나로 합친 대체품이다. CLI가 생성한 `utils.ts`가 이를 쓰므로 그대로 두었다.
- **생성 컴포넌트 4개만 설치**: 지금 필요한 것만 설치한다. 다이얼로그, 토스트 등은 쓰는 태스크에서 `npx shadcn add`로 추가한다.
- **ESLint 예외는 `components/ui`만**: shadcn 컴포넌트는 `buttonVariants` 같은 값을 함께 내보내는 것이 표준이다. 규칙을 전체 해제하지 않고 이 폴더에만 적용했다.

## 비고
- 눈으로 보는 브라우저 확인은 하지 않았다. 단위 테스트는 클래스 이름이 붙었는지만 보고(jsdom은 CSS를 계산하지 않는다), 실제 열 수 변화는 빌드된 CSS에 `@media (min-width:48rem){.md\:grid-cols-2}`, `@media (min-width:64rem){.lg\:grid-cols-3}`가 들어 있는 것까지 확인했다. 개발 서버(`/dev-test`)에서 창 폭을 바꿔 보며 1열 → 2열 → 3열이 되는지 직접 확인하면 된다.
- 요청 문구의 `p3`는 Tailwind 클래스 `p-3`으로 해석했다.
- 폰트는 Geist(영문)이다. 한글은 시스템 기본 폰트로 표시된다. 한글 웹폰트를 쓰려면 별도로 정해야 한다.
- 다크 모드 변수는 정의했지만 `.dark` 클래스를 켜는 토글은 없다. 필요해지면 별도 태스크로 한다.
- 다른 문서에 적힌 `shadcn-ui` 패키지명(quickstart.md)은 현재 `shadcn`이다. 문서는 수정하지 않았다.
- Git 저장소가 아니라 커밋은 없다. 작업 전 설정 파일은 임시 폴더에 백업해 두었다.
