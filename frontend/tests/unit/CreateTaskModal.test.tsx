import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import CreateTaskModal from '../../src/components/task/CreateTaskModal'
import { ApiError } from '../../src/services/api-client'
import { makeFile } from '../fixtures/files'

function renderModal(onSubmit = vi.fn().mockResolvedValue(undefined)) {
  const onClose = vi.fn()
  render(<CreateTaskModal onSubmit={onSubmit} onClose={onClose} />)
  return { onSubmit, onClose }
}

async function typeTitle(title = 'Add Todo Function') {
  await userEvent.type(screen.getByLabelText('태스크 제목'), title)
}

const submitButton = () => screen.getByRole('button', { name: '태스크 만들기' })

describe('CreateTaskModal 구성', () => {
  it('제목 입력, 설명 입력, 업로드 방식 탭 3개를 보여주고 기본은 파일 탭이다', () => {
    renderModal()

    expect(screen.getByRole('dialog', { name: '새 태스크 만들기' })).toBeInTheDocument()
    expect(screen.getByLabelText('태스크 제목')).toBeInTheDocument()
    expect(screen.getByLabelText('설명 (선택)')).toBeInTheDocument()
    expect(screen.getAllByRole('tab').map((tab) => tab.textContent)).toEqual([
      '파일',
      '폴더',
      '코드 붙여넣기',
    ])
    expect(screen.getByRole('tab', { name: '파일' })).toHaveAttribute('aria-selected', 'true')
    expect(screen.getByLabelText('파일 선택')).toBeInTheDocument()
  })

  it('탭을 바꾸면 해당 업로드 방식이 나온다', async () => {
    renderModal()

    await userEvent.click(screen.getByRole('tab', { name: '폴더' }))
    expect(screen.getByLabelText('폴더 선택')).toBeInTheDocument()

    await userEvent.click(screen.getByRole('tab', { name: '코드 붙여넣기' }))
    expect(screen.getByLabelText('프로그래밍 언어')).toBeInTheDocument()
  })

  it('탭을 오가도 고른 파일이 유지된다', async () => {
    renderModal()
    await userEvent.upload(screen.getByLabelText('파일 선택'), makeFile('keep.py'))

    await userEvent.click(screen.getByRole('tab', { name: '폴더' }))
    await userEvent.click(screen.getByRole('tab', { name: '파일' }))

    expect(screen.getByText('keep.py')).toBeInTheDocument()
  })

  it('취소를 누르면 닫는다', async () => {
    const { onClose } = renderModal()

    await userEvent.click(screen.getByRole('button', { name: '취소' }))

    expect(onClose).toHaveBeenCalled()
  })
})

describe('CreateTaskModal 입력 검증', () => {
  it('제목이 5자 미만이면 오류를 보여주고 제출하지 않는다', async () => {
    const { onSubmit } = renderModal()
    await typeTitle('abcd')
    await userEvent.upload(screen.getByLabelText('파일 선택'), makeFile('a.py'))

    await userEvent.click(submitButton())

    expect(screen.getByText('태스크 제목은 최소 5자 이상이어야 합니다.')).toBeInTheDocument()
    expect(onSubmit).not.toHaveBeenCalled()
  })

  it('설명이 500자를 넘으면 오류를 보여준다', async () => {
    const { onSubmit } = renderModal()
    await typeTitle()
    await userEvent.click(screen.getByLabelText('설명 (선택)'))
    await userEvent.paste('a'.repeat(501))
    await userEvent.upload(screen.getByLabelText('파일 선택'), makeFile('a.py'))

    await userEvent.click(submitButton())

    expect(screen.getByText('태스크 설명은 최대 500자까지 입력 가능합니다.')).toBeInTheDocument()
    expect(onSubmit).not.toHaveBeenCalled()
  })

  it('파일 탭에서 파일이 없으면 오류를 보여준다', async () => {
    const { onSubmit } = renderModal()
    await typeTitle()

    await userEvent.click(submitButton())

    expect(screen.getByText('업로드할 파일을 한 개 이상 선택하세요.')).toBeInTheDocument()
    expect(onSubmit).not.toHaveBeenCalled()
  })

  it('붙여넣기 탭에서 언어를 고르지 않으면 오류를 보여준다', async () => {
    const { onSubmit } = renderModal()
    await typeTitle()
    await userEvent.click(screen.getByRole('tab', { name: '코드 붙여넣기' }))
    await userEvent.click(screen.getByLabelText('코드'))
    await userEvent.paste('print(1)')

    await userEvent.click(submitButton())

    expect(screen.getByText('프로그래밍 언어를 선택하세요.')).toBeInTheDocument()
    expect(onSubmit).not.toHaveBeenCalled()
  })
})

describe('CreateTaskModal 제출', () => {
  it('파일 업로드: 제목·설명·파일로 onSubmit을 호출하고 닫는다', async () => {
    const { onSubmit, onClose } = renderModal()
    const file = makeFile('a.py')
    await typeTitle('  Add Todo Function  ')
    await userEvent.click(screen.getByLabelText('설명 (선택)'))
    await userEvent.paste(' 설명입니다 ')
    await userEvent.upload(screen.getByLabelText('파일 선택'), file)

    await userEvent.click(submitButton())

    expect(onSubmit).toHaveBeenCalledWith({
      title: 'Add Todo Function',
      description: '설명입니다',
      uploadMethod: 'file',
      files: [file],
    })
    expect(onClose).toHaveBeenCalled()
  })

  it('설명을 비우면 description은 null이다', async () => {
    const { onSubmit } = renderModal()
    await typeTitle()
    await userEvent.upload(screen.getByLabelText('파일 선택'), makeFile('a.py'))

    await userEvent.click(submitButton())

    expect(onSubmit).toHaveBeenCalledWith(expect.objectContaining({ description: null }))
  })

  it('폴더 업로드: uploadMethod가 folder다', async () => {
    const { onSubmit } = renderModal()
    const file = makeFile('app.py', 10, 'todo/app.py')
    await typeTitle()
    await userEvent.click(screen.getByRole('tab', { name: '폴더' }))
    await userEvent.upload(screen.getByLabelText('폴더 선택'), file)

    await userEvent.click(submitButton())

    expect(onSubmit).toHaveBeenCalledWith({
      title: 'Add Todo Function',
      description: null,
      uploadMethod: 'folder',
      files: [file],
    })
  })

  it('코드 붙여넣기: code와 language로 보낸다', async () => {
    const { onSubmit } = renderModal()
    await typeTitle()
    await userEvent.click(screen.getByRole('tab', { name: '코드 붙여넣기' }))
    await userEvent.selectOptions(screen.getByLabelText('프로그래밍 언어'), 'python')
    await userEvent.click(screen.getByLabelText('코드'))
    await userEvent.paste('print(1)')

    await userEvent.click(submitButton())

    expect(onSubmit).toHaveBeenCalledWith({
      title: 'Add Todo Function',
      description: null,
      uploadMethod: 'paste',
      code: 'print(1)',
      language: 'python',
    })
  })

  it('서버 오류는 모달 안에 보여주고 닫지 않는다', async () => {
    const onSubmit = vi.fn().mockRejectedValue(
      new ApiError({
        code: 'file_too_large',
        message: '파일 크기가 10MB를 초과합니다.',
        status: 413,
      }),
    )
    const { onClose } = renderModal(onSubmit)
    await typeTitle()
    await userEvent.upload(screen.getByLabelText('파일 선택'), makeFile('a.py'))

    await userEvent.click(submitButton())

    expect(await screen.findByText('파일 크기가 10MB를 초과합니다.')).toBeInTheDocument()
    expect(onClose).not.toHaveBeenCalled()
  })

  it('제출 중에는 버튼이 "만드는 중..."으로 바뀌고 비활성화된다', async () => {
    renderModal(vi.fn().mockReturnValue(new Promise(() => undefined)))
    await typeTitle()
    await userEvent.upload(screen.getByLabelText('파일 선택'), makeFile('a.py'))

    await userEvent.click(submitButton())

    expect(screen.getByRole('button', { name: '만드는 중...' })).toBeDisabled()
    expect(screen.getByRole('button', { name: '취소' })).toBeDisabled()
  })
})
