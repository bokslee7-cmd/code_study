import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import AppShell from '../../src/components/layout/AppShell'
import { ApiError } from '../../src/services/api-client'
import { logout } from '../../src/services/auth-service'
import { useAuthStore } from '../../src/stores/auth-store'

vi.mock('../../src/services/auth-service')

const user = { id: 'u-1', email: 'learner@example.com', skillLevel: 'Complete Beginner' }

function renderShell() {
  return render(
    <MemoryRouter initialEntries={['/dashboard']}>
      <Routes>
        <Route path="/login" element={<p>로그인 화면</p>} />
        <Route element={<AppShell />}>
          <Route path="/dashboard" element={<p>대시보드 내용</p>} />
        </Route>
      </Routes>
    </MemoryRouter>,
  )
}

beforeEach(() => {
  useAuthStore.getState().setSession({ accessToken: 'access-1', user, expiresIn: 900 })
})

afterEach(() => {
  vi.resetAllMocks()
  useAuthStore.getState().clearSession()
})

describe('AppShell', () => {
  it('상단에 로그인한 사용자의 이메일과 로그아웃 버튼을 보여주고 하위 페이지를 그린다', () => {
    renderShell()

    expect(screen.getByText('learner@example.com')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '로그아웃' })).toBeInTheDocument()
    expect(screen.getByText('대시보드 내용')).toBeInTheDocument()
  })

  it('로그아웃 버튼을 누르면 서버에 로그아웃을 요청하고 세션을 비운 뒤 로그인 화면으로 이동한다', async () => {
    vi.mocked(logout).mockResolvedValue(undefined)
    renderShell()

    await userEvent.click(screen.getByRole('button', { name: '로그아웃' }))

    expect(await screen.findByText('로그인 화면')).toBeInTheDocument()
    expect(logout).toHaveBeenCalledTimes(1)
    expect(useAuthStore.getState().accessToken).toBeNull()
    expect(useAuthStore.getState().user).toBeNull()
  })

  it('서버 로그아웃이 실패해도 로컬 세션은 비우고 로그인 화면으로 이동한다', async () => {
    vi.mocked(logout).mockRejectedValue(
      new ApiError({ code: 'network_error', message: '연결 실패' }),
    )
    renderShell()

    await userEvent.click(screen.getByRole('button', { name: '로그아웃' }))

    await waitFor(() => expect(screen.getByText('로그인 화면')).toBeInTheDocument())
    expect(useAuthStore.getState().accessToken).toBeNull()
  })
})
