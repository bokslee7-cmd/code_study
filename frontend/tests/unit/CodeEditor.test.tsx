import { render, screen } from '@testing-library/react'
import CodeEditor from '../../src/components/document/CodeEditor'

const mocks = vi.hoisted(() => {
  const collection = { clear: vi.fn() }
  const scrollListeners: Array<() => void> = []
  const editor = {
    createDecorationsCollection: vi.fn(() => collection),
    revealLineInCenter: vi.fn(),
    getVisibleRanges: vi.fn(() => [{ startLineNumber: 12 }]),
    onDidScrollChange: vi.fn((listener: () => void) => {
      scrollListeners.push(listener)
      return { dispose: vi.fn() }
    }),
  }
  return { collection, scrollListeners, editor, lastProps: { current: null as unknown } }
})

vi.mock('@monaco-editor/react', async () => {
  const React = await import('react')
  function FakeEditor(props: {
    value: string
    language: string
    path?: string
    loading?: React.ReactNode
    onMount?: (editor: unknown, monaco: unknown) => void
  }) {
    mocks.lastProps.current = props
    React.useEffect(() => {
      props.onMount?.(mocks.editor, {})
      // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [])
    return (
      <div data-testid="monaco" data-language={props.language} data-path={props.path}>
        {props.value}
      </div>
    )
  }
  return { default: FakeEditor }
})

type EditorProps = {
  options: { readOnly: boolean }
  loading: string
}

beforeEach(() => {
  vi.clearAllMocks()
  mocks.scrollListeners.length = 0
})

describe('CodeEditor', () => {
  it('값과 언어를 Monaco에 넘기고 읽기 전용 옵션을 쓴다', () => {
    render(<CodeEditor value="print(1)" language="py" path="main.py" />)

    const editor = screen.getByTestId('monaco')
    expect(editor).toHaveTextContent('print(1)')
    expect(editor).toHaveAttribute('data-language', 'python')
    expect(editor).toHaveAttribute('data-path', 'main.py')
    expect((mocks.lastProps.current as EditorProps).options.readOnly).toBe(true)
  })

  it('불러오는 동안 보여줄 안내 문구를 넘긴다', () => {
    render(<CodeEditor value="" language="python" />)

    expect((mocks.lastProps.current as EditorProps).loading).toBe('코드 편집기를 불러오는 중...')
  })

  it('highlightLine이 있으면 그 줄을 강조하고 가운데로 스크롤한다', () => {
    render(<CodeEditor value="a" language="python" highlightLine={7} />)

    expect(mocks.editor.createDecorationsCollection).toHaveBeenCalledWith([
      expect.objectContaining({
        range: { startLineNumber: 7, startColumn: 1, endLineNumber: 7, endColumn: 1 },
        options: expect.objectContaining({ isWholeLine: true }),
      }),
    ])
    expect(mocks.editor.revealLineInCenter).toHaveBeenCalledWith(7)
  })

  it('highlightLine이 바뀌면 이전 강조를 지운다', () => {
    const { rerender } = render(<CodeEditor value="a" language="python" highlightLine={7} />)

    rerender(<CodeEditor value="a" language="python" highlightLine={null} />)

    expect(mocks.collection.clear).toHaveBeenCalled()
  })

  it('스크롤하면 화면 맨 위 줄 번호를 알린다', () => {
    const onTopLineChange = vi.fn()
    render(<CodeEditor value="a" language="python" onTopLineChange={onTopLineChange} />)

    mocks.scrollListeners[0]()

    expect(onTopLineChange).toHaveBeenCalledWith(12)
  })

  it('강조로 인한 프로그램 스크롤은 줄 번호 알림에서 제외한다', () => {
    const onTopLineChange = vi.fn()
    render(
      <CodeEditor
        value="a"
        language="python"
        highlightLine={7}
        onTopLineChange={onTopLineChange}
      />,
    )

    mocks.scrollListeners[0]()
    expect(onTopLineChange).not.toHaveBeenCalled()

    mocks.scrollListeners[0]()
    expect(onTopLineChange).toHaveBeenCalledWith(12)
  })
})
