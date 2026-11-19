import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const frontendRoot = resolve(__dirname, '../..')
const read = (path: string) => readFileSync(resolve(frontendRoot, path), 'utf-8')

describe('Tailwind CSS 설정', () => {
  it('index.css가 Tailwind를 불러온다', () => {
    expect(read('src/index.css')).toMatch(/@import\s+["']tailwindcss["']/)
  })

  it('index.css가 shadcn 테마 변수(라이트/다크)를 정의한다', () => {
    const css = read('src/index.css')

    expect(css).toMatch(/:root\s*\{/)
    expect(css).toMatch(/\.dark\s*\{/)
    expect(css).toContain('--background')
    expect(css).toContain('--primary')
  })

  it('main.tsx가 index.css를 불러온다', () => {
    expect(read('src/main.tsx')).toMatch(/import\s+['"]\.\/index\.css['"]/)
  })

  it('vite 설정에 Tailwind 플러그인과 @ 별칭이 있다', () => {
    const config = read('vite.config.ts')

    expect(config).toContain('@tailwindcss/vite')
    expect(config).toMatch(/['"]@['"]\s*:/)
  })

  it('tsconfig에 @/* 경로 별칭이 있다', () => {
    expect(read('tsconfig.json')).toMatch(/"@\/\*"\s*:\s*\[\s*"\.\/src\/\*"\s*\]/)
  })
})

describe('shadcn/ui 설정(components.json)', () => {
  const config = JSON.parse(read('components.json')) as {
    tailwind: { css: string; cssVariables: boolean }
    aliases: Record<string, string>
    tsx: boolean
  }

  it('TypeScript와 CSS 변수 테마를 쓴다', () => {
    expect(config.tsx).toBe(true)
    expect(config.tailwind.cssVariables).toBe(true)
  })

  it('Tailwind CSS 진입 파일이 src/index.css를 가리킨다', () => {
    expect(config.tailwind.css).toBe('src/index.css')
  })

  it('별칭이 @/ 아래 src 구조와 맞는다', () => {
    expect(config.aliases.components).toBe('@/components')
    expect(config.aliases.utils).toBe('@/lib/utils')
    expect(config.aliases.ui).toBe('@/components/ui')
  })
})
