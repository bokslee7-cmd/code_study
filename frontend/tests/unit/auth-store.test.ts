import { AxiosError, type AxiosAdapter, type InternalAxiosRequestConfig } from 'axios'
import { apiClient } from '../../src/services/api-client'
import { selectIsAuthenticated, useAuthStore, type AuthUser } from '../../src/stores/auth-store'

const user: AuthUser = { id: 'u-1', email: 'learner@example.com', skillLevel: 'Complete Beginner' }

afterEach(() => {
  useAuthStore.getState().clearSession()
  localStorage.clear()
  sessionStorage.clear()
})

describe('useAuthStore 초기 상태', () => {
  it('로그인 전에는 토큰과 사용자 정보가 없다', () => {
    const state = useAuthStore.getState()

    expect(state.accessToken).toBeNull()
    expect(state.user).toBeNull()
    expect(selectIsAuthenticated(state)).toBe(false)
  })
})

describe('setSession', () => {
  it('액세스 토큰과 사용자 정보를 저장하고 인증된 상태로 바꾼다', () => {
    useAuthStore.getState().setSession({ accessToken: 'access-1', user })

    const state = useAuthStore.getState()
    expect(state.accessToken).toBe('access-1')
    expect(state.user).toEqual(user)
    expect(selectIsAuthenticated(state)).toBe(true)
  })
})

describe('setAccessToken', () => {
  it('토큰 갱신 시 사용자 정보는 그대로 두고 토큰만 교체한다', () => {
    useAuthStore.getState().setSession({ accessToken: 'access-1', user })

    useAuthStore.getState().setAccessToken('access-2')

    const state = useAuthStore.getState()
    expect(state.accessToken).toBe('access-2')
    expect(state.user).toEqual(user)
  })
})

describe('clearSession', () => {
  it('로그아웃하면 토큰과 사용자 정보를 모두 지운다', () => {
    useAuthStore.getState().setSession({ accessToken: 'access-1', user })

    useAuthStore.getState().clearSession()

    const state = useAuthStore.getState()
    expect(state.accessToken).toBeNull()
    expect(state.user).toBeNull()
    expect(selectIsAuthenticated(state)).toBe(false)
  })
})

describe('토큰 보관 위치', () => {
  it('XSS로 읽히지 않도록 localStorage/sessionStorage에 토큰을 저장하지 않는다', () => {
    useAuthStore.getState().setSession({ accessToken: 'secret-token', user })

    const stored = JSON.stringify({ ...localStorage }) + JSON.stringify({ ...sessionStorage })
    expect(stored).not.toContain('secret-token')
  })
})

describe('api-client 연동', () => {
  function captureAuthorization() {
    let authorization: unknown
    const adapter: AxiosAdapter = async (config: InternalAxiosRequestConfig) => {
      authorization = config.headers.get('Authorization')
      if (authorization === undefined) {
        throw new AxiosError('no auth', AxiosError.ERR_BAD_REQUEST, config)
      }
      return { data: {}, status: 200, statusText: '', headers: {}, config }
    }
    return { adapter, read: () => authorization }
  }

  it('로그인 상태에서는 저장된 토큰이 Authorization 헤더로 붙는다', async () => {
    useAuthStore.getState().setSession({ accessToken: 'access-1', user })
    const { adapter, read } = captureAuthorization()

    await apiClient.get('/ping', { adapter })

    expect(read()).toBe('Bearer access-1')
  })

  it('토큰이 갱신되면 이후 요청부터 새 토큰이 붙는다', async () => {
    useAuthStore.getState().setSession({ accessToken: 'access-1', user })
    useAuthStore.getState().setAccessToken('access-2')
    const { adapter, read } = captureAuthorization()

    await apiClient.get('/ping', { adapter })

    expect(read()).toBe('Bearer access-2')
  })

  it('로그아웃 후에는 Authorization 헤더가 붙지 않는다', async () => {
    useAuthStore.getState().setSession({ accessToken: 'access-1', user })
    useAuthStore.getState().clearSession()
    const { adapter } = captureAuthorization()

    await expect(apiClient.get('/ping', { adapter })).rejects.toBeDefined()
  })
})
