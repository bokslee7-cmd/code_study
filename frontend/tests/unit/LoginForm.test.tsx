import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import LoginForm from '../../src/components/auth/LoginForm'

async function fill(email: string, password: string) {
  if (email) await userEvent.type(screen.getByLabelText('이메일'), email)
  if (password) await userEvent.type(screen.getByLabelText('비밀번호'), password)
}

const submitButton = () => screen.getByRole('button', { name: /^로그인/ })

describe('LoginForm 렌더링', () => {
  it('이메일/비밀번호 입력란과 로그인 버튼을 보여준다', () => {
    render(<LoginForm onSubmit={vi.fn()} />)

    expect(screen.getByLabelText('이메일')).toHaveAttribute('type', 'email')
    expect(screen.getByLabelText('비밀번호')).toHaveAttribute('type', 'password')
    expect(submitButton()).toBeEnabled()
  })

  it('처음에는 오류 메시지가 없다', () => {
    render(<LoginForm onSubmit={vi.fn()} />)

    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })
})

describe('LoginForm 클라이언트 검증', () => {
  it('빈 값으로 제출하면 안내를 보여주고 제출하지 않는다', async () => {
    const onSubmit = vi.fn()
    render(<LoginForm onSubmit={onSubmit} />)

    await userEvent.click(submitButton())

    expect(screen.getByText('이메일을 입력하세요.')).toBeInTheDocument()
    expect(screen.getByText('비밀번호를 입력하세요.')).toBeInTheDocument()
    expect(onSubmit).not.toHaveBeenCalled()
  })

  it('오류가 있는 입력란에는 aria-invalid가 켜지고 오류 문구와 연결된다', async () => {
    render(<LoginForm onSubmit={vi.fn()} />)

    await userEvent.click(submitButton())

    const email = screen.getByLabelText('이메일')
    expect(email).toHaveAttribute('aria-invalid', 'true')
    expect(email).toHaveAccessibleDescription('이메일을 입력하세요.')
    expect(screen.getByLabelText('비밀번호')).toHaveAttribute('aria-invalid', 'true')
  })

  it('이메일 형식이 틀리면 형식 안내를 보여준다', async () => {
    const onSubmit = vi.fn()
    render(<LoginForm onSubmit={onSubmit} />)

    await fill('not-an-email', 'password123')
    await userEvent.click(submitButton())

    expect(screen.getByText('올바른 이메일 형식이 아닙니다.')).toBeInTheDocument()
    expect(onSubmit).not.toHaveBeenCalled()
  })

  it('로그인에서는 비밀번호 길이를 제한하지 않는다(가입 때 규칙이 바뀌어도 기존 사용자를 막지 않기 위해)', async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined)
    render(<LoginForm onSubmit={onSubmit} />)

    await fill('learner@example.com', 'short')
    await userEvent.click(submitButton())

    expect(onSubmit).toHaveBeenCalledWith({ email: 'learner@example.com', password: 'short' })
  })
})

describe('LoginForm 제출', () => {
  it('올바른 값이면 이메일 앞뒤 공백을 지운 값으로 onSubmit을 호출한다', async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined)
    render(<LoginForm onSubmit={onSubmit} />)

    await fill('  learner@example.com  ', 'password123')
    await userEvent.click(submitButton())

    expect(onSubmit).toHaveBeenCalledWith({
      email: 'learner@example.com',
      password: 'password123',
    })
  })

  it('제출 중에는 버튼이 비활성화되고 "로그인 중..."으로 바뀐다', async () => {
    let finish: () => void = () => {}
    const onSubmit = vi.fn(() => new Promise<void>((resolve) => (finish = resolve)))
    render(<LoginForm onSubmit={onSubmit} />)

    await fill('learner@example.com', 'password123')
    await userEvent.click(submitButton())

    const pending = screen.getByRole('button', { name: '로그인 중...' })
    expect(pending).toBeDisabled()

    finish()
    expect(await screen.findByRole('button', { name: '로그인' })).toBeEnabled()
  })

  it('서버 오류 메시지를 alert로 보여주고 다시 제출할 수 있게 한다', async () => {
    const onSubmit = vi
      .fn()
      .mockRejectedValue(new Error('이메일 또는 비밀번호가 올바르지 않습니다.'))
    render(<LoginForm onSubmit={onSubmit} />)

    await fill('learner@example.com', 'password123')
    await userEvent.click(submitButton())

    expect(await screen.findByRole('alert')).toHaveTextContent(
      '이메일 또는 비밀번호가 올바르지 않습니다.',
    )
    expect(submitButton()).toBeEnabled()
  })

  it('다시 제출하면 이전 서버 오류는 사라진다', async () => {
    const onSubmit = vi
      .fn()
      .mockRejectedValueOnce(new Error('일시 오류'))
      .mockResolvedValueOnce(undefined)
    render(<LoginForm onSubmit={onSubmit} />)

    await fill('learner@example.com', 'password123')
    await userEvent.click(submitButton())
    expect(await screen.findByRole('alert')).toHaveTextContent('일시 오류')

    await userEvent.click(submitButton())

    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })
})
