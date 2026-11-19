import { StrictMode, type ReactNode } from 'react'
import { act, renderHook } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { useAuth, useAuthSession } from '../../src/hooks/useAuth'
import { ApiError } from '../../src/services/api-client'
import { fetchMe, logout, refresh } from '../../src/services/auth-service'
import { useAuthStore } from '../../src/stores/auth-store'

vi.mock('../../src/services/auth-service')

const user = { id: 'u-1', email: 'learner@example.com', skillLevel: 'Complete Beginner' }
const unauthorized = new ApiError({ code: 'unauthorized', message: '만료', status: 401 })

function wrapper({ children }: { children: ReactNode }) {
  return (
    <MemoryRouter initialEntries={['/dashboard']}>
      <Routes>
        <Route path="/dashboard" element={children} />
        <Route path="/login" element={<p>로그인 화면</p>} />
      </Routes>
    </MemoryRouter>
  )
}

// fake timer 아래에서 보류 중인 Promise와 타이머를 함께 흘려보낸다.
async function advance(ms: number) {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(ms)
  })
}

beforeEach(() => {
  vi.useFakeTimers()
  useAuthStore.setState({ isRestoring: true })
})

afterEach(() => {
  vi.useRealTimers()
  vi.resetAllMocks()
  useAuthStore.getState().clearSession()
})

describe('useAuthSession: 앱 시작 시 세션 복구', () => {
  it('refresh -> me 순서로 호출해 세션을 복구하고 복구 중 상태를 끝낸다', async () => {
    vi.mocked(refresh).mockResolvedValue({ accessToken: 'access-1', expiresIn: 900 })
    vi.mocked(fetchMe).mockResolvedValue(user)

    renderHook(() => useAuthSession(), { wrapper })
    await advance(0)

    expect(fetchMe).toHaveBeenCalledWith('access-1')
    const state = useAuthStore.getState()
    expect(state.accessToken).toBe('access-1')
    expect(state.user).toEqual(user)
    expect(state.tokenExpiresAt).not.toBeNull()
    expect(state.isRestoring).toBe(false)
  })

  it('refresh가 401이면 비로그인으로 확정하고 me는 호출하지 않는다', async () => {
    vi.mocked(refresh).mockRejectedValue(unauthorized)

    renderHook(() => useAuthSession(), { wrapper })
    await advance(0)

    expect(fetchMe).not.toHaveBeenCalled()
    const state = useAuthStore.getState()
    expect(state.accessToken).toBeNull()
    expect(state.isRestoring).toBe(false)
  })

  it('me가 실패하면 부분 세션을 남기지 않고 비로그인으로 확정한다', async () => {
    vi.mocked(refresh).mockResolvedValue({ accessToken: 'access-1', expiresIn: 900 })
    vi.mocked(fetchMe).mockRejectedValue(unauthorized)

    renderHook(() => useAuthSession(), { wrapper })
    await advance(0)

    const state = useAuthStore.getState()
    expect(state.accessToken).toBeNull()
    expect(state.user).toBeNull()
    expect(state.isRestoring).toBe(false)
  })

  it('복구가 끝나기 전에는 복구 중 상태가 유지된다', async () => {
    vi.mocked(refresh).mockReturnValue(new Promise(() => {}))

    renderHook(() => useAuthSession(), { wrapper })
    await advance(0)

    expect(useAuthStore.getState().isRestoring).toBe(true)
  })

  it('StrictMode(개발 모드 이중 실행)에서도 refresh는 한 번만 호출한다', async () => {
    vi.mocked(refresh).mockResolvedValue({ accessToken: 'access-1', expiresIn: 900 })
    vi.mocked(fetchMe).mockResolvedValue(user)

    renderHook(() => useAuthSession(), {
      wrapper: ({ children }) => <StrictMode>{wrapper({ children })}</StrictMode>,
    })
    await advance(0)

    expect(refresh).toHaveBeenCalledTimes(1)
  })
})

describe('useAuthSession: 만료 직전 자동 갱신', () => {
  async function mountRestored() {
    vi.mocked(refresh).mockResolvedValueOnce({ accessToken: 'access-1', expiresIn: 900 })
    vi.mocked(fetchMe).mockResolvedValue(user)
    const rendered = renderHook(() => useAuthSession(), { wrapper })
    await advance(0)
    vi.mocked(refresh).mockClear()
    return rendered
  }

  it('만료 60초 전에 refresh를 호출하고 새 토큰으로 교체한다', async () => {
    await mountRestored()
    vi.mocked(refresh).mockResolvedValue({ accessToken: 'access-2', expiresIn: 900 })

    await advance(839_000)
    expect(refresh).not.toHaveBeenCalled()

    await advance(1_000)
    expect(refresh).toHaveBeenCalledTimes(1)
    const state = useAuthStore.getState()
    expect(state.accessToken).toBe('access-2')
    expect(state.user).toEqual(user)
  })

  it('갱신에 성공하면 새 만료 시각 기준으로 다음 갱신을 예약한다', async () => {
    await mountRestored()
    vi.mocked(refresh).mockResolvedValue({ accessToken: 'access-2', expiresIn: 900 })

    await advance(840_000)
    await advance(840_000)

    expect(refresh).toHaveBeenCalledTimes(2)
  })

  it('갱신이 실패하면(401 등) 세션을 지운다', async () => {
    await mountRestored()
    vi.mocked(refresh).mockRejectedValue(unauthorized)

    await advance(840_000)

    const state = useAuthStore.getState()
    expect(state.accessToken).toBeNull()
    expect(state.user).toBeNull()
  })

  it('갱신 중에 로그아웃되면 새 토큰으로 세션을 되살리지 않는다', async () => {
    await mountRestored()
    let resolveRefresh: (value: { accessToken: string; expiresIn: number }) => void = () => {}
    vi.mocked(refresh).mockReturnValue(new Promise((resolve) => (resolveRefresh = resolve)))

    await advance(840_000)
    act(() => useAuthStore.getState().clearSession())
    resolveRefresh({ accessToken: 'access-2', expiresIn: 900 })
    await advance(0)

    expect(useAuthStore.getState().accessToken).toBeNull()
  })

  it('로그인으로 세션이 생기면 그 expiresIn 기준으로 갱신을 예약한다', async () => {
    vi.mocked(refresh).mockRejectedValueOnce(unauthorized)
    renderHook(() => useAuthSession(), { wrapper })
    await advance(0)
    vi.mocked(refresh).mockClear()
    vi.mocked(refresh).mockResolvedValue({ accessToken: 'access-2', expiresIn: 900 })

    act(() => useAuthStore.getState().setSession({ accessToken: 'access-1', user, expiresIn: 120 }))
    await advance(59_000)
    expect(refresh).not.toHaveBeenCalled()
    await advance(1_000)

    expect(refresh).toHaveBeenCalledTimes(1)
  })

  it('로그아웃하면 예약된 갱신이 취소된다', async () => {
    await mountRestored()

    act(() => useAuthStore.getState().clearSession())
    await advance(900_000)

    expect(refresh).not.toHaveBeenCalled()
  })

  it('언마운트하면 예약된 갱신이 취소된다', async () => {
    const { unmount } = await mountRestored()

    unmount()
    await advance(900_000)

    expect(refresh).not.toHaveBeenCalled()
  })
})

describe('useAuth', () => {
  it('현재 사용자와 인증 여부를 돌려준다', () => {
    const { result } = renderHook(() => useAuth(), { wrapper })
    expect(result.current.isAuthenticated).toBe(false)
    expect(result.current.user).toBeNull()

    act(() => useAuthStore.getState().setSession({ accessToken: 'access-1', user }))

    expect(result.current.isAuthenticated).toBe(true)
    expect(result.current.user).toEqual(user)
  })

  it('logout은 서버에 로그아웃을 요청하고 세션을 지운 뒤 /login으로 이동한다', async () => {
    vi.mocked(logout).mockResolvedValue(undefined)
    useAuthStore.getState().setSession({ accessToken: 'access-1', user })
    const view = renderHook(() => useAuth(), { wrapper })
    const loginText = () => document.body.textContent

    await act(async () => {
      await view.result.current.logout()
    })

    expect(logout).toHaveBeenCalledTimes(1)
    expect(useAuthStore.getState().accessToken).toBeNull()
    expect(loginText()).toContain('로그인 화면')
  })

  it('서버 로그아웃이 실패해도 로컬 세션은 반드시 지우고 /login으로 이동한다', async () => {
    vi.mocked(logout).mockRejectedValue(new Error('network'))
    useAuthStore.getState().setSession({ accessToken: 'access-1', user })
    const view = renderHook(() => useAuth(), { wrapper })

    await act(async () => {
      await view.result.current.logout()
    })

    expect(useAuthStore.getState().accessToken).toBeNull()
    expect(document.body.textContent).toContain('로그인 화면')
  })
})
