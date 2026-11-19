import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import ExplanationPanel from '../../src/components/document/ExplanationPanel'
import { makeContent } from '../fixtures/document'

const navButtons = () =>
  within(screen.getByRole('navigation', { name: '챕터 이동' })).getAllByRole('button')

beforeEach(() => {
  Element.prototype.scrollIntoView = vi.fn()
})

describe('ExplanationPanel 챕터 네비게이션', () => {
  it('7개 챕터 버튼을 번호와 제목으로 보여준다', () => {
    render(<ExplanationPanel content={makeContent()} failedChapters={[]} />)

    expect(navButtons().map((button) => button.textContent)).toEqual([
      '1. 이 코드가 하는 일',
      '2. 알아야 할 기본 개념',
      '3. 코드 구조 한눈에 보기',
      '4. 코드 한 줄씩 완전 해부',
      '5. 실행 흐름 따라가기',
      '6. 핵심 개념 정리',
      '7. 자주 하는 실수와 해결법',
    ])
  })

  it('처음에는 1장을 보여주고 현재 챕터 버튼을 강조한다', () => {
    render(<ExplanationPanel content={makeContent()} failedChapters={[]} />)

    expect(screen.getByText('두 수를 더해 주는 코드입니다.')).toBeInTheDocument()
    expect(navButtons()[0]).toHaveAttribute('aria-current', 'step')
    expect(navButtons()[1]).not.toHaveAttribute('aria-current')
  })

  it('챕터 버튼을 누르면 그 챕터로 바뀌고 강조도 옮겨 간다', async () => {
    render(<ExplanationPanel content={makeContent()} failedChapters={[]} />)

    await userEvent.click(navButtons()[1])

    expect(
      screen.getByRole('heading', { level: 3, name: '알아야 할 기본 개념' }),
    ).toBeInTheDocument()
    expect(screen.queryByText('두 수를 더해 주는 코드입니다.')).not.toBeInTheDocument()
    expect(navButtons()[1]).toHaveAttribute('aria-current', 'step')
    expect(navButtons()[0]).not.toHaveAttribute('aria-current')
  })

  it('4장에서는 줄별 해설을 보여준다', async () => {
    render(<ExplanationPanel content={makeContent()} failedChapters={[]} />)

    await userEvent.click(navButtons()[3])

    expect(screen.getAllByRole('article')).toHaveLength(2)
    expect(screen.getByText('더한 결과를 돌려준다')).toBeInTheDocument()
  })
})

describe('ExplanationPanel 범용 챕터 렌더링', () => {
  it('3장은 플로우차트와 파일별 역할을 보여준다', async () => {
    render(<ExplanationPanel content={makeContent()} failedChapters={[]} />)

    await userEvent.click(navButtons()[2])

    expect(screen.getByText('[시작] -> [add 호출] -> [끝]')).toBeInTheDocument()
    expect(screen.getByText('main.py')).toBeInTheDocument()
    expect(screen.getByText('덧셈 함수가 들어 있는 파일')).toBeInTheDocument()
  })

  it('5장은 단계별 동작과 변수 값을 보여준다', async () => {
    render(<ExplanationPanel content={makeContent()} failedChapters={[]} />)

    await userEvent.click(navButtons()[4])

    expect(screen.getByText('add(2, 3)을 부른다')).toBeInTheDocument()
    expect(screen.getByText('a=2, b=3')).toBeInTheDocument()
    expect(screen.getByText('재료 2와 3이 함수에 들어간다')).toBeInTheDocument()
  })

  it('6장은 개념의 의미·이유·적용 위치를 보여준다', async () => {
    render(<ExplanationPanel content={makeContent()} failedChapters={[]} />)

    await userEvent.click(navButtons()[5])

    expect(screen.getByText('반환값')).toBeInTheDocument()
    expect(screen.getByText('함수가 돌려주는 결과')).toBeInTheDocument()
    expect(screen.getByText('결과를 다른 곳에서 쓰려고')).toBeInTheDocument()
    expect(screen.getByText('return a + b')).toBeInTheDocument()
  })

  it('7장은 실수 제목과 틀린/올바른 코드, 이유, 해결법을 보여준다', async () => {
    render(<ExplanationPanel content={makeContent()} failedChapters={[]} />)

    await userEvent.click(navButtons()[6])

    expect(screen.getByText('return을 빼먹음')).toBeInTheDocument()
    expect(screen.getByText('def add(a, b): a + b')).toBeInTheDocument()
    expect(screen.getByText('def add(a, b): return a + b')).toBeInTheDocument()
    expect(screen.getByText('결과가 None이 된다')).toBeInTheDocument()
    expect(screen.getByText('return을 붙인다')).toBeInTheDocument()
  })
})

describe('ExplanationPanel 실패·빈 챕터', () => {
  it('실패한 챕터는 내용 대신 생성 실패 안내를 보여준다', async () => {
    render(
      <ExplanationPanel
        content={makeContent({ chapter4: { generation_failed: true } })}
        failedChapters={['chapter4']}
      />,
    )

    await userEvent.click(navButtons()[3])

    expect(screen.getByText('생성 실패')).toBeInTheDocument()
    expect(
      screen.getByText('이 섹션을 만들지 못했습니다. 질문하기로 보충할 수 있어요.'),
    ).toBeInTheDocument()
    expect(screen.queryByRole('article')).not.toBeInTheDocument()
  })

  it('실패한 챕터의 네비게이션 버튼은 기본 제목과 실패 표시를 가진다', () => {
    render(
      <ExplanationPanel
        content={makeContent({ chapter4: { generation_failed: true } })}
        failedChapters={['chapter4']}
      />,
    )

    expect(navButtons()[3]).toHaveTextContent('4. 코드 한 줄씩 완전 해부')
    expect(navButtons()[3]).toHaveTextContent('생성 실패')
  })

  it('failedChapters에 있으면 내용이 남아 있어도 실패로 본다', async () => {
    render(<ExplanationPanel content={makeContent()} failedChapters={['chapter1']} />)

    expect(screen.getByText('생성 실패')).toBeInTheDocument()
    expect(screen.queryByText('두 수를 더해 주는 코드입니다.')).not.toBeInTheDocument()
  })

  it('내용이 아직 없는 챕터는 준비 중 안내를 보여준다', async () => {
    render(<ExplanationPanel content={{}} failedChapters={[]} />)

    expect(screen.getByText('이 챕터의 내용이 아직 없습니다.')).toBeInTheDocument()
    expect(navButtons()[0]).toHaveTextContent('1. 이 코드가 하는 일')
  })
})

describe('ExplanationPanel 줄 동기화', () => {
  it('4장에서 줄 선택을 위로 전달한다', async () => {
    const onLineSelect = vi.fn()
    render(
      <ExplanationPanel content={makeContent()} failedChapters={[]} onLineSelect={onLineSelect} />,
    )
    await userEvent.click(navButtons()[3])

    await userEvent.click(screen.getByRole('button', { name: '줄 2' }))

    expect(onLineSelect).toHaveBeenCalledWith({ filePath: '', line: 2 })
  })

  it('4장에서 activeLine·scrollTarget을 4장 컴포넌트에 전달한다', async () => {
    render(
      <ExplanationPanel
        content={makeContent()}
        failedChapters={[]}
        activeLine={{ filePath: 'main.py', line: 2 }}
        scrollTarget={{ filePath: 'main.py', line: 2 }}
      />,
    )

    await userEvent.click(navButtons()[3])

    expect(screen.getAllByRole('article')[1]).toHaveAttribute('aria-current', 'true')
    expect(Element.prototype.scrollIntoView).toHaveBeenCalled()
  })
})
