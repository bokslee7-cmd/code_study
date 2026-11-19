import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import App from '../../src/App'
import { ApiError } from '../../src/services/api-client'
import { fetchMe, refresh } from '../../src/services/auth-service'
import { useAuthStore } from '../../src/stores/auth-store'

vi.mock('../../src/services/auth-service')

const user = { id: 'u-1', email: 'learner@example.com', skillLevel: 'Complete Beginner' }

function renderAt(path: string) {
  return render(
    <QueryClientProvider client={new QueryClient()}>
      <MemoryRouter initialEntries={[path]}>
        <App />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

beforeEach(() => {
  useAuthStore.setState({ isRestoring: true })
})

afterEach(() => {
  vi.resetAllMocks()
  useAuthStore.getState().clearSession()
})

describe('App 인증 라우팅: 비로그인', () => {
  beforeEach(() => {
    vi.mocked(refresh).mockRejectedValue(
      new ApiError({ code: 'unauthorized', message: '로그인 필요', status: 401 }),
    )
  })

  it.each(['/dashboard', '/', '/projects/p1', '/projects/p1/tasks/t1', '/trash'])(
    '%s 접근 시 로그인 페이지로 이동한다',
    async (path) => {
      renderAt(path)

      expect(await screen.findByRole('heading', { name: '로그인' })).toBeInTheDocument()
    },
  )

  it('/login 은 로그인 페이지, /register 는 회원가입 페이지를 보여준다', async () => {
    const login = renderAt('/login')
    expect(await screen.findByLabelText('이메일')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '로그인' })).toBeInTheDocument()
    login.unmount()

    renderAt('/register')
    expect(await screen.findByLabelText('비밀번호 확인')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '회원가입' })).toBeInTheDocument()
  })

  it('/dev-test 는 보호하지 않는다', async () => {
    renderAt('/dev-test')

    expect(await screen.findByRole('heading', { name: '개발용 API 테스트' })).toBeInTheDocument()
  })
})

describe('App 인증 라우팅: 세션 복구', () => {
  it('복구가 끝나기 전에는 로그인으로 보내지 않고 로딩 상태를 보여준다', () => {
    vi.mocked(refresh).mockReturnValue(new Promise(() => {}))

    renderAt('/dashboard')

    expect(screen.getByRole('status')).toHaveTextContent('로그인 상태를 확인하는 중입니다...')
    expect(screen.queryByRole('heading', { name: '로그인' })).not.toBeInTheDocument()
  })

  it('새로고침 후 쿠키로 복구되면 로그인 페이지를 거치지 않고 원래 페이지를 보여준다', async () => {
    vi.mocked(refresh).mockResolvedValue({ accessToken: 'access-1', expiresIn: 900 })
    vi.mocked(fetchMe).mockResolvedValue(user)

    renderAt('/trash')

    expect(await screen.findByRole('heading', { name: '휴지통' })).toBeInTheDocument()
  })
})
