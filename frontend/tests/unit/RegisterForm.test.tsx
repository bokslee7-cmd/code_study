import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import RegisterForm from '../../src/components/auth/RegisterForm'

async function fill(email: string, password: string, confirm: string) {
  if (email) await userEvent.type(screen.getByLabelText('이메일'), email)
  if (password) await userEvent.type(screen.getByLabelText('비밀번호'), password)
  if (confirm) await userEvent.type(screen.getByLabelText('비밀번호 확인'), confirm)
}

const submitButton = () => screen.getByRole('button', { name: /^회원가입/ })

describe('RegisterForm 렌더링', () => {
  it('이메일/비밀번호/비밀번호 확인 입력란과 회원가입 버튼을 보여준다', () => {
    render(<RegisterForm onSubmit={vi.fn()} />)

    expect(screen.getByLabelText('이메일')).toHaveAttribute('type', 'email')
    expect(screen.getByLabelText('비밀번호')).toHaveAttribute('type', 'password')
    expect(screen.getByLabelText('비밀번호 확인')).toHaveAttribute('type', 'password')
    expect(submitButton()).toBeEnabled()
  })
})

describe('RegisterForm 클라이언트 검증', () => {
  it('빈 값으로 제출하면 안내를 보여주고 제출하지 않는다', async () => {
    const onSubmit = vi.fn()
    render(<RegisterForm onSubmit={onSubmit} />)

    await userEvent.click(submitButton())

    expect(screen.getByText('이메일을 입력하세요.')).toBeInTheDocument()
    expect(screen.getByText('비밀번호를 입력하세요.')).toBeInTheDocument()
    expect(onSubmit).not.toHaveBeenCalled()
  })

  it('이메일 형식이 틀리면 형식 안내를 보여준다', async () => {
    const onSubmit = vi.fn()
    render(<RegisterForm onSubmit={onSubmit} />)

    await fill('broken', 'password123', 'password123')
    await userEvent.click(submitButton())

    expect(screen.getByLabelText('이메일')).toHaveAttribute('aria-invalid', 'true')
    expect(screen.getByText('올바른 이메일 형식이 아닙니다.')).toBeInTheDocument()
    expect(onSubmit).not.toHaveBeenCalled()
  })

  it('비밀번호가 8자 미만이면 길이 안내를 보여준다', async () => {
    const onSubmit = vi.fn()
    render(<RegisterForm onSubmit={onSubmit} />)

    await fill('learner@example.com', '1234567', '1234567')
    await userEvent.click(submitButton())

    expect(screen.getByText('비밀번호는 8자 이상이어야 합니다.')).toBeInTheDocument()
    expect(onSubmit).not.toHaveBeenCalled()
  })

  it('비밀번호 확인이 다르면 불일치 안내를 확인란에 보여준다', async () => {
    const onSubmit = vi.fn()
    render(<RegisterForm onSubmit={onSubmit} />)

    await fill('learner@example.com', 'password123', 'password124')
    await userEvent.click(submitButton())

    const confirm = screen.getByLabelText('비밀번호 확인')
    expect(confirm).toHaveAttribute('aria-invalid', 'true')
    expect(confirm).toHaveAccessibleDescription('비밀번호가 일치하지 않습니다.')
    expect(onSubmit).not.toHaveBeenCalled()
  })
})

describe('RegisterForm 제출', () => {
  it('올바른 값이면 비밀번호 확인을 제외한 이메일/비밀번호만 onSubmit에 넘긴다', async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined)
    render(<RegisterForm onSubmit={onSubmit} />)

    await fill(' learner@example.com ', 'password123', 'password123')
    await userEvent.click(submitButton())

    expect(onSubmit).toHaveBeenCalledWith({
      email: 'learner@example.com',
      password: 'password123',
    })
  })

  it('제출 중에는 버튼이 비활성화되고 "가입 중..."으로 바뀐다', async () => {
    let finish: () => void = () => {}
    const onSubmit = vi.fn(() => new Promise<void>((resolve) => (finish = resolve)))
    render(<RegisterForm onSubmit={onSubmit} />)

    await fill('learner@example.com', 'password123', 'password123')
    await userEvent.click(submitButton())

    expect(screen.getByRole('button', { name: '가입 중...' })).toBeDisabled()

    finish()
    expect(await screen.findByRole('button', { name: '회원가입' })).toBeEnabled()
  })

  it('서버 오류 메시지(예: 중복 이메일)를 alert로 보여준다', async () => {
    const onSubmit = vi.fn().mockRejectedValue(new Error('이미 가입된 이메일입니다.'))
    render(<RegisterForm onSubmit={onSubmit} />)

    await fill('learner@example.com', 'password123', 'password123')
    await userEvent.click(submitButton())

    expect(await screen.findByRole('alert')).toHaveTextContent('이미 가입된 이메일입니다.')
    expect(submitButton()).toBeEnabled()
  })
})
