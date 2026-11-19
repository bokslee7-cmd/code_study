import { render, screen, within } from '@testing-library/react'
import Chapter2 from '../../src/components/document/chapters/Chapter2'
import type { Chapter2Content } from '../../src/types/document'

const chapter: Chapter2Content = {
  title: '알아야 할 기본 개념',
  concepts: [
    {
      name: '함수',
      explanation: '작업을 묶어 둔 코드 덩어리',
      analogy: '요리 레시피',
      example: 'def add(a, b): return a + b',
      use_cases: '같은 계산을 여러 번 할 때',
    },
    {
      name: '변수',
      explanation: '이름표가 붙은 상자',
      analogy: '서랍',
      example: 'x = 1',
      use_cases: '값을 기억해 둘 때',
    },
  ],
}

describe('Chapter2', () => {
  it('제목을 보여준다', () => {
    render(<Chapter2 chapter={chapter} />)

    expect(
      screen.getByRole('heading', { level: 3, name: '알아야 할 기본 개념' }),
    ).toBeInTheDocument()
  })

  it('개념마다 카드를 만든다', () => {
    render(<Chapter2 chapter={chapter} />)

    expect(screen.getAllByRole('article')).toHaveLength(2)
    expect(screen.getByRole('heading', { level: 4, name: '함수' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { level: 4, name: '변수' })).toBeInTheDocument()
  })

  it('카드에 설명·비유·예시·사용처를 모두 보여준다', () => {
    render(<Chapter2 chapter={chapter} />)

    const card = screen.getAllByRole('article')[0]
    expect(within(card).getByText('설명')).toBeInTheDocument()
    expect(within(card).getByText('작업을 묶어 둔 코드 덩어리')).toBeInTheDocument()
    expect(within(card).getByText('비유')).toBeInTheDocument()
    expect(within(card).getByText('요리 레시피')).toBeInTheDocument()
    expect(within(card).getByText('예시')).toBeInTheDocument()
    expect(within(card).getByText('def add(a, b): return a + b')).toBeInTheDocument()
    expect(within(card).getByText('사용처')).toBeInTheDocument()
    expect(within(card).getByText('같은 계산을 여러 번 할 때')).toBeInTheDocument()
  })

  it('개념이 없으면 안내 문구를 보여준다', () => {
    render(<Chapter2 chapter={{ title: '알아야 할 기본 개념', concepts: [] }} />)

    expect(screen.getByText('설명할 개념이 없습니다.')).toBeInTheDocument()
  })
})
