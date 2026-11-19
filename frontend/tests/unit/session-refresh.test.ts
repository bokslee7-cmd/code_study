import { AxiosError, type AxiosAdapter } from 'axios'
import { ApiError, apiClient } from '../../src/services/api-client'
import { refresh } from '../../src/services/auth-service'
import '../../src/services/session-refresh'
import { useAuthStore } from '../../src/stores/auth-store'

vi.mock('../../src/services/auth-service')

const user = { id: 'u-1', email: 'learner@example.com', skillLevel: 'Complete Beginner' }

// 'new-token'만 통과시키는 가짜 서버.
const server: AxiosAdapter = async (config) => {
  const ok = config.headers.get('Authorization') === 'Bearer new-token'
  const response = {
    data: ok ? { ok: true } : {},
    status: ok ? 200 : 401,
    statusText: '',
    headers: {},
    config,
  }
  if (ok) return response
  throw new AxiosError('failed', AxiosError.ERR_BAD_RESPONSE, config, null, response)
}

beforeEach(() => {
  useAuthStore.getState().setSession({ accessToken: 'old-token', user, expiresIn: 60 })
})

afterEach(() => {
  vi.resetAllMocks()
  useAuthStore.getState().clearSession()
})

describe('session-refresh: 401 갱신을 스토어와 연결한다', () => {
  it('갱신에 성공하면 새 토큰을 스토어에 저장하고 요청을 재시도한다', async () => {
    vi.mocked(refresh).mockResolvedValue({ accessToken: 'new-token', expiresIn: 900 })

    const response = await apiClient.get('/projects', { adapter: server })

    expect(response.status).toBe(200)
    const state = useAuthStore.getState()
    expect(state.accessToken).toBe('new-token')
    expect(state.user).toEqual(user)
    expect(state.tokenExpiresAt).toBeGreaterThan(Date.now() + 800_000)
  })

  it('갱신에 실패하면 세션을 비워 로그인 화면으로 보내고 401 오류를 돌려준다', async () => {
    vi.mocked(refresh).mockRejectedValue(
      new ApiError({ code: 'unauthorized', message: '리프레시 만료', status: 401 }),
    )

    const error = await apiClient.get('/projects', { adapter: server }).catch((e: unknown) => e)

    expect((error as ApiError).status).toBe(401)
    const state = useAuthStore.getState()
    expect(state.accessToken).toBeNull()
    expect(state.user).toBeNull()
  })

  it('갱신 응답을 기다리는 사이 로그아웃됐다면 세션을 되살리지 않는다', async () => {
    vi.mocked(refresh).mockImplementation(async () => {
      useAuthStore.getState().clearSession()
      return { accessToken: 'new-token', expiresIn: 900 }
    })

    await apiClient.get('/projects', { adapter: server }).catch(() => undefined)

    expect(useAuthStore.getState().accessToken).toBeNull()
  })
})
