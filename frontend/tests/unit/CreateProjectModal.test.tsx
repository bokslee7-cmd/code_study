import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import CreateProjectModal from '../../src/components/project/CreateProjectModal'
import { ApiError } from '../../src/services/api-client'

function renderModal(onSubmit = vi.fn().mockResolvedValue(undefined), onClose = vi.fn()) {
  render(<CreateProjectModal onSubmit={onSubmit} onClose={onClose} />)
  return { onSubmit, onClose }
}

const titleInput = () => screen.getByLabelText('프로젝트 제목')
const submitButton = () => screen.getByRole('button', { name: /^만들기/ })

describe('CreateProjectModal 접근성', () => {
  it('제목이 연결된 모달 대화상자(role=dialog, aria-modal)로 열린다', () => {
    renderModal()

    const dialog = screen.getByRole('dialog', { name: '새 프로젝트 만들기' })
    expect(dialog).toHaveAttribute('aria-modal', 'true')
  })

  it('열리면 제목 입력란에 포커스가 간다', () => {
    renderModal()

    expect(titleInput()).toHaveFocus()
  })

  it('입력란은 라벨로 연결되어 있고 설명은 선택 항목이다', () => {
    renderModal()

    expect(titleInput()).toBeInTheDocument()
    expect(screen.getByLabelText('설명 (선택)')).toBeInTheDocument()
  })

  it('ESC 키를 누르면 닫힌다', async () => {
    const { onClose } = renderModal()

    await userEvent.keyboard('{Escape}')

    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('취소 버튼을 누르면 닫힌다', async () => {
    const { onClose } = renderModal()

    await userEvent.click(screen.getByRole('button', { name: '취소' }))

    expect(onClose).toHaveBeenCalledTimes(1)
  })
})

describe('CreateProjectModal 클라이언트 검증', () => {
  it('제목이 비어 있으면 안내를 보여주고 제출하지 않는다', async () => {
    const { onSubmit } = renderModal()

    await userEvent.click(submitButton())

    expect(screen.getByText('프로젝트 제목을 입력하세요.')).toBeInTheDocument()
    expect(titleInput()).toHaveAttribute('aria-invalid', 'true')
    expect(onSubmit).not.toHaveBeenCalled()
  })

  it('공백만 입력해도 제출하지 않는다', async () => {
    const { onSubmit } = renderModal()

    await userEvent.type(titleInput(), '    ')
    await userEvent.click(submitButton())

    expect(screen.getByText('프로젝트 제목을 입력하세요.')).toBeInTheDocument()
    expect(onSubmit).not.toHaveBeenCalled()
  })

  it('256자 제목은 길이 안내를 보여주고 제출하지 않는다', async () => {
    const { onSubmit } = renderModal()

    await userEvent.click(titleInput())
    await userEvent.paste('가'.repeat(256))
    await userEvent.click(submitButton())

    expect(screen.getByText('프로젝트 제목은 255자 이하로 입력하세요.')).toBeInTheDocument()
    expect(onSubmit).not.toHaveBeenCalled()
  })
})

describe('CreateProjectModal 제출', () => {
  it('제목과 설명의 앞뒤 공백을 지워 제출하고, 성공하면 닫는다', async () => {
    const { onSubmit, onClose } = renderModal()

    await userEvent.type(titleInput(), '  My Todo App  ')
    await userEvent.type(screen.getByLabelText('설명 (선택)'), ' 할 일 앱 ')
    await userEvent.click(submitButton())

    await waitFor(() => expect(onClose).toHaveBeenCalledTimes(1))
    expect(onSubmit).toHaveBeenCalledWith({ title: 'My Todo App', description: '할 일 앱' })
  })

  it('설명을 비워 두면 description을 null로 보낸다', async () => {
    const { onSubmit } = renderModal()

    await userEvent.type(titleInput(), 'My Todo App')
    await userEvent.click(submitButton())

    await waitFor(() => expect(onSubmit).toHaveBeenCalled())
    expect(onSubmit).toHaveBeenCalledWith({ title: 'My Todo App', description: null })
  })

  it('제출 중에는 버튼이 비활성화되고 다시 눌러도 한 번만 제출한다', async () => {
    let finish: () => void = () => undefined
    const onSubmit = vi.fn(() => new Promise<void>((resolve) => (finish = resolve)))
    renderModal(onSubmit)

    await userEvent.type(titleInput(), 'My Todo App')
    await userEvent.click(submitButton())

    const pendingButton = await screen.findByRole('button', { name: '만드는 중...' })
    expect(pendingButton).toBeDisabled()
    await userEvent.click(pendingButton)
    expect(onSubmit).toHaveBeenCalledTimes(1)

    finish()
  })

  it('제출 중에 Enter 키로 다시 제출해도 한 번만 제출한다', async () => {
    const onSubmit = vi.fn(() => new Promise<void>(() => undefined))
    renderModal(onSubmit)

    await userEvent.type(titleInput(), 'My Todo App')
    await userEvent.click(submitButton())
    await screen.findByRole('button', { name: '만드는 중...' })
    await userEvent.type(titleInput(), '{Enter}')

    expect(onSubmit).toHaveBeenCalledTimes(1)
  })

  it('제출 중에는 ESC로 닫히지 않는다', async () => {
    const onSubmit = vi.fn(() => new Promise<void>(() => undefined))
    const { onClose } = renderModal(onSubmit)

    await userEvent.type(titleInput(), 'My Todo App')
    await userEvent.click(submitButton())
    await screen.findByRole('button', { name: '만드는 중...' })
    await userEvent.keyboard('{Escape}')

    expect(onClose).not.toHaveBeenCalled()
  })
})

describe('CreateProjectModal 서버 오류', () => {
  it('서버가 제목 검증 오류(400)를 주면 제목 필드 오류로 보여주고 닫지 않는다', async () => {
    const onSubmit = vi.fn().mockRejectedValue(
      new ApiError({
        code: 'validation_error',
        message: '제목은 1자 이상 255자 이하여야 합니다.',
        status: 400,
        details: { field: 'title' },
      }),
    )
    const { onClose } = renderModal(onSubmit)

    await userEvent.type(titleInput(), 'My Todo App')
    await userEvent.click(submitButton())

    expect(await screen.findByText('제목은 1자 이상 255자 이하여야 합니다.')).toBeInTheDocument()
    expect(titleInput()).toHaveAttribute('aria-invalid', 'true')
    expect(onClose).not.toHaveBeenCalled()
    expect(submitButton()).toBeEnabled()
  })

  it('그 밖의 서버 오류는 대화상자 안에 알림으로 보여주고 닫지 않는다', async () => {
    const onSubmit = vi
      .fn()
      .mockRejectedValue(
        new ApiError({ code: 'network_error', message: '서버에 연결할 수 없습니다.' }),
      )
    const { onClose } = renderModal(onSubmit)

    await userEvent.type(titleInput(), 'My Todo App')
    await userEvent.click(submitButton())

    expect(await screen.findByRole('alert')).toHaveTextContent('서버에 연결할 수 없습니다.')
    expect(onClose).not.toHaveBeenCalled()
  })
})
