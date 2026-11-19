import { cn } from '@/lib/utils'

describe('cn', () => {
  it('여러 클래스 이름을 공백으로 합친다', () => {
    expect(cn('flex', 'items-center')).toBe('flex items-center')
  })

  it('거짓 값(false, null, undefined)은 무시한다', () => {
    expect(cn('flex', false, null, undefined, 'gap-2')).toBe('flex gap-2')
  })

  it('조건부 객체 문법을 지원한다', () => {
    expect(cn('p-2', { 'font-bold': true, underline: false })).toBe('p-2 font-bold')
  })

  it('충돌하는 Tailwind 클래스는 나중 것이 이긴다', () => {
    expect(cn('p-2', 'p-4')).toBe('p-4')
    expect(cn('text-red-500', 'text-blue-500')).toBe('text-blue-500')
  })
})
