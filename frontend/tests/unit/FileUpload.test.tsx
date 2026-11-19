import { fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useState } from 'react'
import FileUpload from '../../src/components/upload/FileUpload'
import { makeFile } from '../fixtures/files'

interface HarnessProps {
  initial?: File[]
  onChange?: (files: File[]) => void
}

function Harness({ initial = [], onChange }: HarnessProps) {
  const [files, setFiles] = useState<File[]>(initial)
  return (
    <FileUpload
      files={files}
      onChange={(next) => {
        onChange?.(next)
        setFiles(next)
      }}
    />
  )
}

describe('FileUpload', () => {
  it('파일 선택 입력은 여러 파일을 받을 수 있다', () => {
    render(<Harness />)
    const input = screen.getByLabelText('파일 선택')
    expect(input).toHaveAttribute('type', 'file')
    expect(input).toHaveAttribute('multiple')
  })

  it('파일을 고르면 onChange로 전달하고 목록에 보여준다', async () => {
    const onChange = vi.fn()
    render(<Harness onChange={onChange} />)
    const file = makeFile('app.py')

    await userEvent.upload(screen.getByLabelText('파일 선택'), file)

    expect(onChange).toHaveBeenCalledWith([file])
    expect(screen.getByText('app.py')).toBeInTheDocument()
  })

  it('끌어다 놓으면 파일이 추가된다', () => {
    const onChange = vi.fn()
    render(<Harness onChange={onChange} />)
    const file = makeFile('drop.js')

    fireEvent.drop(screen.getByRole('group', { name: '파일 끌어놓기 영역' }), {
      dataTransfer: { files: [file] },
    })

    expect(onChange).toHaveBeenCalledWith([file])
  })

  it('기존 파일에 이어서 추가하고 같은 파일은 중복으로 넣지 않는다', async () => {
    const onChange = vi.fn()
    render(<Harness initial={[makeFile('a.py', 5)]} onChange={onChange} />)

    await userEvent.upload(screen.getByLabelText('파일 선택'), [
      makeFile('a.py', 5),
      makeFile('b.py'),
    ])

    const next = onChange.mock.calls[0][0] as File[]
    expect(next.map((f) => f.name)).toEqual(['a.py', 'b.py'])
  })

  it('지원하지 않는 확장자는 추가하지 않고 오류를 보여준다', async () => {
    const onChange = vi.fn()
    render(<Harness onChange={onChange} />)

    await userEvent.upload(screen.getByLabelText('파일 선택'), makeFile('photo.png'))

    expect(onChange).not.toHaveBeenCalled()
    expect(screen.getByRole('alert')).toHaveTextContent('지원하지 않는 파일 형식입니다: photo.png')
  })

  it('이후 올바르게 추가하면 오류가 사라진다', async () => {
    render(<Harness />)
    await userEvent.upload(screen.getByLabelText('파일 선택'), makeFile('photo.png'))
    await userEvent.upload(screen.getByLabelText('파일 선택'), makeFile('ok.py'))

    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('21번째 파일은 거부한다', async () => {
    const initial = Array.from({ length: 20 }, (_, i) => makeFile(`f${i}.py`))
    render(<Harness initial={initial} />)

    await userEvent.upload(screen.getByLabelText('파일 선택'), makeFile('extra.py'))

    expect(screen.getByRole('alert')).toHaveTextContent('업로드당 최대 20개 파일까지 가능합니다.')
  })

  it('제거 버튼으로 파일을 뺄 수 있다', async () => {
    const onChange = vi.fn()
    render(<Harness initial={[makeFile('a.py'), makeFile('b.py')]} onChange={onChange} />)

    await userEvent.click(screen.getByRole('button', { name: 'a.py 제거' }))

    expect((onChange.mock.calls[0][0] as File[]).map((f) => f.name)).toEqual(['b.py'])
    expect(screen.queryByText('a.py')).not.toBeInTheDocument()
  })

  it('disabled이면 입력과 제거 버튼을 막는다', () => {
    render(<FileUpload files={[makeFile('a.py')]} onChange={vi.fn()} disabled />)

    expect(screen.getByLabelText('파일 선택')).toBeDisabled()
    expect(screen.getByRole('button', { name: 'a.py 제거' })).toBeDisabled()
  })
})
