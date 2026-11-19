import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom'
import ProtectedRoute from '../../src/components/auth/ProtectedRoute'
import { useAuthStore } from '../../src/stores/auth-store'

function LoginProbe() {
  const location = useLocation()
  const from = (location.state as { from?: { pathname: string; search: string } } | null)?.from
  return <p>로그인 화면 from={from ? `${from.pathname}${from.search}` : 'none'}</p>
}

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/login" element={<LoginProbe />} />
        <Route element={<ProtectedRoute />}>
          <Route path="/secret" element={<p>비밀 페이지</p>} />
        </Route>
      </Routes>
    </MemoryRouter>,
  )
}

const user = { id: 'u-1', email: 'learner@example.com', skillLevel: 'Complete Beginner' }

afterEach(() => {
  useAuthStore.getState().clearSession()
  useAuthStore.setState({ isRestoring: true })
})

describe('ProtectedRoute', () => {
  it('세션 복구 중에는 로딩 상태만 보여주고 리다이렉트하지 않는다', () => {
    useAuthStore.setState({ isRestoring: true })
    renderAt('/secret')

    expect(screen.getByRole('status')).toHaveTextContent('로그인 상태를 확인하는 중입니다...')
    expect(screen.queryByText('비밀 페이지')).not.toBeInTheDocument()
    expect(screen.queryByText(/로그인 화면/)).not.toBeInTheDocument()
  })

  it('복구가 끝났는데 비로그인이면 원래 위치(from)를 담아 /login으로 보낸다', () => {
    useAuthStore.setState({ isRestoring: false })
    renderAt('/secret?tab=1')

    expect(screen.getByText('로그인 화면 from=/secret?tab=1')).toBeInTheDocument()
  })

  it('로그인 상태면 하위 라우트를 보여준다', () => {
    useAuthStore.setState({ isRestoring: false })
    useAuthStore.getState().setSession({ accessToken: 'access-1', user })
    renderAt('/secret')

    expect(screen.getByText('비밀 페이지')).toBeInTheDocument()
  })

  it('복구 중이어도 이미 로그인된 상태라면 로딩이 아니라 페이지를 보여준다', () => {
    useAuthStore.setState({ isRestoring: true })
    useAuthStore.getState().setSession({ accessToken: 'access-1', user })
    renderAt('/secret')

    expect(screen.getByText('비밀 페이지')).toBeInTheDocument()
  })
})
