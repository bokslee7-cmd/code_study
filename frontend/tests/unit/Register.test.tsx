import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import Login from '../../src/pages/Login'
import Register from '../../src/pages/Register'
import { register } from '../../src/services/auth-service'

vi.mock('../../src/services/auth-service')

function renderRegister() {
  return render(
    <MemoryRouter initialEntries={['/register']}>
      <Routes>
        <Route path="/register" element={<Register />} />
        <Route path="/login" element={<Login />} />
      </Routes>
    </MemoryRouter>,
  )
}

async function submit() {
  await userEvent.type(screen.getByLabelText('이메일'), 'learner@example.com')
  await userEvent.type(screen.getByLabelText('비밀번호'), 'password123')
  await userEvent.type(screen.getByLabelText('비밀번호 확인'), 'password123')
  await userEvent.click(screen.getByRole('button', { name: '회원가입' }))
}

afterEach(() => {
  vi.resetAllMocks()
})

describe('Register 페이지', () => {
  it('"회원가입" 제목과 폼, 로그인 링크를 보여준다', () => {
    renderRegister()

    expect(screen.getByRole('heading', { name: '회원가입' })).toBeInTheDocument()
    expect(screen.getByLabelText('비밀번호 확인')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: '로그인' })).toHaveAttribute('href', '/login')
  })

  it('가입에 성공하면 가입 완료 안내와 함께 로그인 페이지로 이동한다', async () => {
    vi.mocked(register).mockResolvedValue({
      id: 'u-1',
      email: 'learner@example.com',
      skillLevel: 'Complete Beginner',
    })
    renderRegister()

    await submit()

    expect(register).toHaveBeenCalledWith({
      email: 'learner@example.com',
      password: 'password123',
    })
    expect(await screen.findByRole('heading', { name: '로그인' })).toBeInTheDocument()
    expect(screen.getByRole('status')).toHaveTextContent(
      '회원가입이 완료되었습니다. 로그인해 주세요.',
    )
  })

  it('가입에 실패하면 서버 메시지를 보여주고 이 페이지에 머문다', async () => {
    vi.mocked(register).mockRejectedValue(new Error('이미 가입된 이메일입니다.'))
    renderRegister()

    await submit()

    expect(await screen.findByRole('alert')).toHaveTextContent('이미 가입된 이메일입니다.')
    expect(screen.getByRole('heading', { name: '회원가입' })).toBeInTheDocument()
  })
})
