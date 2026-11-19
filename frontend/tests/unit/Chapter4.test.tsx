import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import Chapter4 from '../../src/components/document/chapters/Chapter4'
import type { Chapter4Content } from '../../src/types/document'
import { makeLineExplanation } from '../fixtures/document'

const chapter: Chapter4Content = {
  title: '코드 한 줄씩 완전 해부',
  explanations: [
    makeLineExplanation({ line_number: 1, alternatives: 'lambda a, b: a + b' }),
    makeLineExplanation({
      line_number: 5,
      code: '    return a + b',
      what_it_does: '더한 결과를 돌려준다',
      syntax_breakdown: 'return은 결과를 돌려준다는 뜻이다',
      analogy: '',
      important_notes: '들여쓰기를 빼먹지 말 것',
    }),
    makeLineExplanation({ line_number: 9, file_path: 'util.py', code: 'print(1)' }),
  ],
}

const scrollIntoView = vi.fn()

beforeEach(() => {
  scrollIntoView.mockClear()
  Element.prototype.scrollIntoView = scrollIntoView
})

const items = () => screen.getAllByRole('article')

describe('Chapter4', () => {
  it('제목과 줄마다 해설 항목을 보여준다', () => {
    render(<Chapter4 chapter={chapter} />)

    expect(
      screen.getByRole('heading', { level: 3, name: '코드 한 줄씩 완전 해부' }),
    ).toBeInTheDocument()
    expect(items()).toHaveLength(3)
  })

  it('항목에 줄 번호, 코드, 하는 일, 문법 풀이를 보여준다', () => {
    render(<Chapter4 chapter={chapter} />)

    const first = items()[0]
    expect(within(first).getByRole('button', { name: '줄 1' })).toBeInTheDocument()
    expect(within(first).getByText('def add(a, b):')).toBeInTheDocument()
    expect(within(first).getByText('add라는 함수를 만든다')).toBeInTheDocument()
    expect(within(first).getByText('def는 함수를 만든다는 뜻이다')).toBeInTheDocument()
  })

  it('비어 있지 않은 비유·다른 방법·주의할 점만 보여준다', () => {
    render(<Chapter4 chapter={chapter} />)

    const first = items()[0]
    expect(within(first).getByText('레시피에 이름을 붙이는 것')).toBeInTheDocument()
    expect(within(first).getByText('lambda a, b: a + b')).toBeInTheDocument()
    expect(within(first).queryByText('주의할 점')).not.toBeInTheDocument()

    const second = items()[1]
    expect(within(second).queryByText('비유')).not.toBeInTheDocument()
    expect(within(second).queryByText('다른 방법')).not.toBeInTheDocument()
    expect(within(second).getByText('들여쓰기를 빼먹지 말 것')).toBeInTheDocument()
  })

  it('여러 파일의 줄이면 파일 경로를 함께 보여준다', () => {
    render(<Chapter4 chapter={chapter} />)

    expect(within(items()[2]).getByText('util.py')).toBeInTheDocument()
    expect(within(items()[0]).queryByText('util.py')).not.toBeInTheDocument()
  })

  it('activeLine과 같은 줄의 항목을 현재 항목으로 표시한다', () => {
    render(<Chapter4 chapter={chapter} activeLine={{ filePath: '', line: 5 }} />)

    expect(items()[1]).toHaveAttribute('aria-current', 'true')
    expect(items()[0]).not.toHaveAttribute('aria-current')
  })

  it('줄 번호 버튼을 누르면 그 줄을 알린다', async () => {
    const onLineSelect = vi.fn()
    render(<Chapter4 chapter={chapter} onLineSelect={onLineSelect} />)

    await userEvent.click(screen.getByRole('button', { name: '줄 9' }))

    expect(onLineSelect).toHaveBeenCalledWith({ filePath: 'util.py', line: 9 })
  })

  it('scrollTarget 줄 이하 중 가장 가까운 항목으로 스크롤한다', () => {
    render(<Chapter4 chapter={chapter} scrollTarget={{ filePath: '', line: 7 }} />)

    expect(scrollIntoView).toHaveBeenCalledTimes(1)
    expect(scrollIntoView.mock.instances[0]).toBe(items()[1])
  })

  it('scrollTarget이 첫 해설보다 앞 줄이면 첫 항목으로 스크롤한다', () => {
    render(<Chapter4 chapter={chapter} scrollTarget={{ filePath: '', line: 0 }} />)

    expect(scrollIntoView.mock.instances[0]).toBe(items()[0])
  })

  it('scrollTarget이 다른 파일이면 그 파일의 항목으로 스크롤한다', () => {
    render(<Chapter4 chapter={chapter} scrollTarget={{ filePath: 'util.py', line: 20 }} />)

    expect(scrollIntoView.mock.instances[0]).toBe(items()[2])
  })

  it('해설이 없으면 안내 문구를 보여준다', () => {
    render(<Chapter4 chapter={{ title: '코드 한 줄씩 완전 해부', explanations: [] }} />)

    expect(screen.getByText('줄별 해설이 없습니다.')).toBeInTheDocument()
  })
})
