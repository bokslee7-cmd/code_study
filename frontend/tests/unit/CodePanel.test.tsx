import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import CodePanel from '../../src/components/document/CodePanel'
import { makeFile } from '../fixtures/document'

vi.mock('../../src/components/document/CodeEditor', () => ({
  default: (props: {
    value: string
    language: string
    path?: string
    highlightLine?: number | null
    onTopLineChange?: (line: number) => void
  }) => (
    <div
      data-testid="editor"
      data-language={props.language}
      data-path={props.path}
      data-highlight={props.highlightLine ?? ''}
    >
      <pre>{props.value}</pre>
      <button onClick={() => props.onTopLineChange?.(5)}>스크롤</button>
    </div>
  ),
}))

const files = [
  makeFile({ path: 'main.py', content: 'print("main")' }),
  makeFile({ path: 'util.py', content: 'print("util")' }),
]

describe('CodePanel', () => {
  it('파일이 하나면 경로를 보여주고 탭은 만들지 않는다', () => {
    render(<CodePanel files={[makeFile({ path: 'main.py' })]} />)

    expect(screen.getByText('main.py')).toBeInTheDocument()
    expect(screen.queryByRole('tablist')).not.toBeInTheDocument()
    expect(screen.getByTestId('editor')).toHaveAttribute('data-language', 'python')
    expect(screen.getByTestId('editor')).toHaveAttribute('data-path', 'main.py')
  })

  it('파일이 여러 개면 파일 탭을 만들고 첫 파일을 먼저 보여준다', () => {
    render(<CodePanel files={files} />)

    expect(screen.getAllByRole('tab').map((tab) => tab.textContent)).toEqual(['main.py', 'util.py'])
    expect(screen.getByRole('tab', { name: 'main.py' })).toHaveAttribute('aria-selected', 'true')
    expect(screen.getByText('print("main")')).toBeInTheDocument()
  })

  it('탭을 누르면 그 파일의 코드로 바뀐다', async () => {
    render(<CodePanel files={files} />)

    await userEvent.click(screen.getByRole('tab', { name: 'util.py' }))

    expect(screen.getByText('print("util")')).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: 'util.py' })).toHaveAttribute('aria-selected', 'true')
  })

  it('highlight가 현재 파일의 줄이면 그 줄 번호를 편집기에 넘긴다', () => {
    render(<CodePanel files={files} highlight={{ filePath: 'main.py', line: 3 }} />)

    expect(screen.getByTestId('editor')).toHaveAttribute('data-highlight', '3')
  })

  it('파일 경로가 빈 문자열인 highlight는 첫 파일의 줄로 본다', () => {
    render(<CodePanel files={files} highlight={{ filePath: '', line: 2 }} />)

    expect(screen.getByTestId('editor')).toHaveAttribute('data-highlight', '2')
  })

  it('highlight가 다른 파일을 가리키면 그 파일 탭으로 옮겨 간다', () => {
    render(<CodePanel files={files} highlight={{ filePath: 'util.py', line: 4 }} />)

    expect(screen.getByRole('tab', { name: 'util.py' })).toHaveAttribute('aria-selected', 'true')
    expect(screen.getByTestId('editor')).toHaveAttribute('data-highlight', '4')
  })

  it('다른 파일 줄을 가리키는 동안 현재 파일에는 강조를 넘기지 않는다', async () => {
    const { rerender } = render(
      <CodePanel files={files} highlight={{ filePath: 'main.py', line: 3 }} />,
    )

    rerender(<CodePanel files={files} highlight={{ filePath: 'util.py', line: 4 }} />)
    await userEvent.click(screen.getByRole('tab', { name: 'main.py' }))

    expect(screen.getByTestId('editor')).toHaveAttribute('data-highlight', '')
  })

  it('스크롤하면 현재 파일 경로와 맨 위 줄 번호를 알린다', async () => {
    const onVisibleLineChange = vi.fn()
    render(<CodePanel files={files} onVisibleLineChange={onVisibleLineChange} />)

    await userEvent.click(screen.getByRole('tab', { name: 'util.py' }))
    await userEvent.click(screen.getByRole('button', { name: '스크롤' }))

    expect(onVisibleLineChange).toHaveBeenCalledWith({ filePath: 'util.py', line: 5 })
  })

  it('파일이 없으면 안내 문구를 보여준다', () => {
    render(<CodePanel files={[]} />)

    expect(screen.getByText('표시할 코드가 없습니다.')).toBeInTheDocument()
    expect(screen.queryByTestId('editor')).not.toBeInTheDocument()
  })
})
