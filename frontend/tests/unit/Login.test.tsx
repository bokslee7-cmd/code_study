import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes, type To } from 'react-router-dom'
import Login from '../../src/pages/Login'
import { login } from '../../src/services/auth-service'
import { useAuthStore } from '../../src/stores/auth-store'

vi.mock('../../src/services/auth-service')

const serverResult = {
  accessToken: 'access-1',
  expiresIn: 900,
  user: { id: 'u-1', email: 'learner@example.com', skillLevel: 'Complete Beginner' },
}

function renderLogin(entry: To | { pathname: string; state: unknown } = '/login') {
  return render(
    <MemoryRouter initialEntries={[entry as string]}>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/dashboard" element={<h1>대시보드 화면</h1>} />
        <Route path="/projects/:projectId" element={<h1>프로젝트 화면</h1>} />
        <Route path="/register" element={<h1>가입 화면</h1>} />
      </Routes>
    </MemoryRouter>,
  )
}

async function submit(email = 'learner@example.com', password = 'password123') {
  await userEvent.type(screen.getByLabelText('이메일'), email)
  await userEvent.type(screen.getByLabelText('비밀번호'), password)
  await userEvent.click(screen.getByRole('button', { name: '로그인' }))
}

afterEach(() => {
  vi.resetAllMocks()
  useAuthStore.getState().clearSession()
})

describe('Login 페이지', () => {
  it('"로그인" 제목과 폼, 회원가입 링크를 보여준다', () => {
    renderLogin()

    expect(screen.getByRole('heading', { name: '로그인' })).toBeInTheDocument()
    expect(screen.getByLabelText('이메일')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: '회원가입' })).toHaveAttribute('href', '/register')
  })

  it('가입 직후 이동해 왔다면 가입 완료 안내를 보여준다', () => {
    renderLogin({ pathname: '/login', state: { registered: true } })

    expect(screen.getByRole('status')).toHaveTextContent(
      '회원가입이 완료되었습니다. 로그인해 주세요.',
    )
  })

  it('평소에는 가입 완료 안내가 없다', () => {
    renderLogin()

    expect(screen.queryByRole('status')).not.toBeInTheDocument()
  })

  it('로그인에 성공하면 세션을 저장하고 대시보드로 이동한다', async () => {
    vi.mocked(login).mockResolvedValue(serverResult)
    renderLogin()

    await submit()

    expect(login).toHaveBeenCalledWith({ email: 'learner@example.com', password: 'password123' })
    expect(await screen.findByRole('heading', { name: '대시보드 화면' })).toBeInTheDocument()
    const state = useAuthStore.getState()
    expect(state.accessToken).toBe('access-1')
    expect(state.user).toEqual(serverResult.user)
    expect(state.tokenExpiresAt).not.toBeNull()
  })

  it('보호된 페이지에서 넘어왔다면 로그인 후 원래 위치로 돌아간다', async () => {
    vi.mocked(login).mockResolvedValue(serverResult)
    renderLogin({
      pathname: '/login',
      state: { from: { pathname: '/projects/p1', search: '' } },
    })

    await submit()

    expect(await screen.findByRole('heading', { name: '프로젝트 화면' })).toBeInTheDocument()
  })

  it('로그인에 실패하면 서버 메시지를 보여주고 세션을 저장하지 않는다', async () => {
    vi.mocked(login).mockRejectedValue(new Error('이메일 또는 비밀번호가 올바르지 않습니다.'))
    renderLogin()

    await submit()

    expect(await screen.findByRole('alert')).toHaveTextContent(
      '이메일 또는 비밀번호가 올바르지 않습니다.',
    )
    expect(screen.getByRole('heading', { name: '로그인' })).toBeInTheDocument()
    expect(useAuthStore.getState().accessToken).toBeNull()
  })
})
