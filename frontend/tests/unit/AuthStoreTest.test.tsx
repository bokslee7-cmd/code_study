import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import App from '../../src/App'
import AuthStoreTest from '../../src/components/dev/AuthStoreTest'
import { useAuthStore } from '../../src/stores/auth-store'

const userRegion = () => screen.getByRole('region', { name: '사용자 정보' })
const statusRegion = () => screen.getByRole('region', { name: '인증 상태' })

afterEach(() => {
  useAuthStore.getState().clearSession()
})

describe('AuthStoreTest 초기 화면', () => {
  it('로그인 전에는 두 컴포넌트가 모두 "없음/false"를 보여준다', () => {
    render(<AuthStoreTest />)

    expect(userRegion()).toHaveTextContent('사용자 없음')
    expect(statusRegion()).toHaveTextContent('isAuthenticated: false')
    expect(screen.getByRole('button', { name: '사용자 설정' })).toBeEnabled()
    expect(screen.getByRole('button', { name: '인증 초기화' })).toBeEnabled()
  })
})

describe('"사용자 설정" 버튼', () => {
  it('클릭하면 사용자 정보 컴포넌트와 인증 상태 컴포넌트가 동시에 갱신된다', async () => {
    render(<AuthStoreTest />)

    await userEvent.click(screen.getByRole('button', { name: '사용자 설정' }))

    expect(userRegion()).toHaveTextContent('dev-test@example.com')
    expect(statusRegion()).toHaveTextContent('isAuthenticated: true')
  })

  it('스토어에 테스트 사용자와 토큰이 실제로 저장된다', async () => {
    render(<AuthStoreTest />)

    await userEvent.click(screen.getByRole('button', { name: '사용자 설정' }))

    const { user, accessToken } = useAuthStore.getState()
    expect(user?.email).toBe('dev-test@example.com')
    expect(accessToken).not.toBeNull()
  })
})

describe('"인증 초기화" 버튼', () => {
  it('클릭하면 두 컴포넌트가 동시에 초기 상태로 돌아간다', async () => {
    render(<AuthStoreTest />)
    await userEvent.click(screen.getByRole('button', { name: '사용자 설정' }))

    await userEvent.click(screen.getByRole('button', { name: '인증 초기화' }))

    expect(userRegion()).toHaveTextContent('사용자 없음')
    expect(statusRegion()).toHaveTextContent('isAuthenticated: false')
    expect(useAuthStore.getState().user).toBeNull()
  })
})

describe('스토어 외부 변경', () => {
  it('버튼이 아닌 곳에서 스토어가 바뀌어도 두 컴포넌트가 함께 따라간다', () => {
    render(<AuthStoreTest />)

    act(() => {
      useAuthStore.getState().setSession({
        accessToken: 'external-token',
        user: { id: 'u-9', email: 'external@example.com', skillLevel: 'Intermediate' },
      })
    })

    expect(userRegion()).toHaveTextContent('external@example.com')
    expect(statusRegion()).toHaveTextContent('isAuthenticated: true')
  })
})

describe('/dev-test 라우트', () => {
  it('기존 API 테스트와 함께 스토어 테스트 영역을 보여준다', () => {
    render(
      <QueryClientProvider client={new QueryClient()}>
        <MemoryRouter initialEntries={['/dev-test']}>
          <App />
        </MemoryRouter>
      </QueryClientProvider>,
    )

    expect(screen.getByRole('heading', { name: '개발용 API 테스트' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '인증 스토어 테스트' })).toBeInTheDocument()
    expect(userRegion()).toBeInTheDocument()
    expect(statusRegion()).toBeInTheDocument()
  })
})
