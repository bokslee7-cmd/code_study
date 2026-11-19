import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useState } from 'react'
import FolderUpload from '../../src/components/upload/FolderUpload'
import { makeFile } from '../fixtures/files'

interface HarnessProps {
  initial?: File[]
  onChange?: (files: File[]) => void
}

function Harness({ initial = [], onChange }: HarnessProps) {
  const [files, setFiles] = useState<File[]>(initial)
  return (
    <FolderUpload
      files={files}
      onChange={(next) => {
        onChange?.(next)
        setFiles(next)
      }}
    />
  )
}

describe('FolderUpload', () => {
  it('폴더 선택 입력은 webkitdirectory를 쓴다', () => {
    render(<Harness />)
    const input = screen.getByLabelText('폴더 선택')
    expect(input).toHaveAttribute('type', 'file')
    expect(input).toHaveAttribute('webkitdirectory')
  })

  it('폴더 안 파일을 상대 경로와 함께 보여주고 onChange로 전달한다', async () => {
    const onChange = vi.fn()
    render(<Harness onChange={onChange} />)
    const a = makeFile('app.py', 10, 'todo/app.py')
    const b = makeFile('util.py', 10, 'todo/lib/util.py')

    await userEvent.upload(screen.getByLabelText('폴더 선택'), [a, b])

    expect(onChange).toHaveBeenCalledWith([a, b])
    expect(screen.getByText('todo/app.py')).toBeInTheDocument()
    expect(screen.getByText('todo/lib/util.py')).toBeInTheDocument()
  })

  it('.git, node_modules, __pycache__, .DS_Store 는 제외하고 제외 개수를 알려준다', async () => {
    const onChange = vi.fn()
    render(<Harness onChange={onChange} />)
    const keep = makeFile('app.py', 10, 'todo/app.py')

    await userEvent.upload(screen.getByLabelText('폴더 선택'), [
      keep,
      makeFile('config', 10, 'todo/.git/config'),
      makeFile('index.js', 10, 'todo/node_modules/x/index.js'),
      makeFile('a.pyc', 10, 'todo/__pycache__/a.pyc'),
      makeFile('.DS_Store', 10, 'todo/.DS_Store'),
    ])

    expect(onChange).toHaveBeenCalledWith([keep])
    expect(screen.getByRole('status')).toHaveTextContent('4개 항목은 자동으로 제외했습니다.')
  })

  it('지원하지 않는 확장자가 있으면 거부하고 오류를 보여준다', async () => {
    const onChange = vi.fn()
    render(<Harness onChange={onChange} />)

    await userEvent.upload(screen.getByLabelText('폴더 선택'), [
      makeFile('app.py', 10, 'todo/app.py'),
      makeFile('logo.png', 10, 'todo/logo.png'),
    ])

    expect(onChange).not.toHaveBeenCalled()
    expect(screen.getByRole('alert')).toHaveTextContent('지원하지 않는 파일 형식입니다: logo.png')
  })

  it('20개를 넘는 폴더는 거부한다', async () => {
    const files = Array.from({ length: 21 }, (_, i) => makeFile(`f${i}.py`, 10, `d/f${i}.py`))
    render(<Harness />)

    await userEvent.upload(screen.getByLabelText('폴더 선택'), files)

    expect(screen.getByRole('alert')).toHaveTextContent('업로드당 최대 20개 파일까지 가능합니다.')
  })

  it('폴더를 다시 고르면 이전 선택을 대체한다', async () => {
    const onChange = vi.fn()
    render(<Harness initial={[makeFile('old.py', 10, 'old/old.py')]} onChange={onChange} />)
    const next = makeFile('new.py', 10, 'new/new.py')

    await userEvent.upload(screen.getByLabelText('폴더 선택'), next)

    expect(onChange).toHaveBeenCalledWith([next])
    expect(screen.queryByText('old/old.py')).not.toBeInTheDocument()
  })

  it('폴더 선택을 비울 수 있다', async () => {
    const onChange = vi.fn()
    render(<Harness initial={[makeFile('a.py', 10, 'd/a.py')]} onChange={onChange} />)

    await userEvent.click(screen.getByRole('button', { name: '선택 지우기' }))

    expect(onChange).toHaveBeenCalledWith([])
  })

  it('disabled이면 입력을 막는다', () => {
    render(<FolderUpload files={[]} onChange={vi.fn()} disabled />)
    expect(screen.getByLabelText('폴더 선택')).toBeDisabled()
  })
})
