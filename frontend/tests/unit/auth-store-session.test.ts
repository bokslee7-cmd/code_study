import { useAuthStore, type AuthUser } from '../../src/stores/auth-store'

const user: AuthUser = { id: 'u-1', email: 'learner@example.com', skillLevel: 'Complete Beginner' }
const NOW = new Date('2026-11-09T00:00:00Z').getTime()

beforeEach(() => {
  vi.useFakeTimers()
  vi.setSystemTime(NOW)
})

afterEach(() => {
  vi.useRealTimers()
  useAuthStore.getState().clearSession()
})

describe('세션 복구 상태', () => {
  it('앱이 시작될 때는 복구 중(isRestoring)이고 만료 시각은 없다', () => {
    const state = useAuthStore.getState()

    expect(state.isRestoring).toBe(true)
    expect(state.tokenExpiresAt).toBeNull()
  })

  it('finishRestoring을 호출하면 복구 중 상태가 끝난다', () => {
    useAuthStore.getState().finishRestoring()

    expect(useAuthStore.getState().isRestoring).toBe(false)
  })

  it('clearSession은 복구 중 상태를 바꾸지 않는다', () => {
    useAuthStore.setState({ isRestoring: true })
    useAuthStore.getState().clearSession()
    expect(useAuthStore.getState().isRestoring).toBe(true)

    useAuthStore.setState({ isRestoring: false })
    useAuthStore.getState().clearSession()
    expect(useAuthStore.getState().isRestoring).toBe(false)
  })
})

describe('토큰 만료 시각', () => {
  it('setSession에 expiresIn(초)을 주면 만료 시각(ms)을 계산해 저장한다', () => {
    useAuthStore.getState().setSession({ accessToken: 'a1', user, expiresIn: 900 })

    expect(useAuthStore.getState().tokenExpiresAt).toBe(NOW + 900_000)
  })

  it('setSession에 expiresIn이 없으면 만료 시각은 null이다', () => {
    useAuthStore.getState().setSession({ accessToken: 'a1', user })

    expect(useAuthStore.getState().tokenExpiresAt).toBeNull()
  })

  it('setAccessToken에 expiresIn을 주면 만료 시각을 새로 계산한다', () => {
    useAuthStore.getState().setSession({ accessToken: 'a1', user, expiresIn: 900 })
    vi.setSystemTime(NOW + 840_000)

    useAuthStore.getState().setAccessToken('a2', 900)

    const state = useAuthStore.getState()
    expect(state.accessToken).toBe('a2')
    expect(state.tokenExpiresAt).toBe(NOW + 840_000 + 900_000)
  })

  it('clearSession은 만료 시각도 지운다', () => {
    useAuthStore.getState().setSession({ accessToken: 'a1', user, expiresIn: 900 })

    useAuthStore.getState().clearSession()

    expect(useAuthStore.getState().tokenExpiresAt).toBeNull()
  })
})
