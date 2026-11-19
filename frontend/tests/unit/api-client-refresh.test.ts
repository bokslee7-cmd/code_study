import { AxiosError, type AxiosAdapter } from 'axios'
import {
  ApiError,
  apiClient,
  setAuthTokenProvider,
  setUnauthorizedRefresher,
} from '../../src/services/api-client'

// 현재 토큰이 'fresh-token'일 때만 200, 그 외에는 401을 돌려주는 가짜 서버.
function serverAccepting(validToken: string, calls: string[]) {
  const adapter: AxiosAdapter = async (config) => {
    const auth = String(config.headers.get('Authorization') ?? '')
    calls.push(`${config.url} ${auth}`)
    const ok = auth === `Bearer ${validToken}`
    const status = ok ? 200 : config.url === '/boom' ? 500 : 401
    const response = {
      data: ok ? { ok: true } : { error: 'unauthorized', message: '만료' },
      status,
      statusText: '',
      headers: {},
      config,
    }
    if (ok) return response
    throw new AxiosError('failed', AxiosError.ERR_BAD_RESPONSE, config, null, response)
  }
  return adapter
}

let token: string | null
let calls: string[]

beforeEach(() => {
  token = 'stale-token'
  calls = []
  setAuthTokenProvider(() => token)
})

afterEach(() => {
  setAuthTokenProvider(null)
  setUnauthorizedRefresher(null)
})

describe('응답 인터셉터: 401이면 토큰을 갱신하고 한 번 재시도한다', () => {
  it('갱신에 성공하면 새 토큰으로 원래 요청을 다시 보내 성공시킨다', async () => {
    const refresher = vi.fn(async () => {
      token = 'fresh-token'
      return 'fresh-token'
    })
    setUnauthorizedRefresher(refresher)

    const response = await apiClient.get('/projects', {
      adapter: serverAccepting('fresh-token', calls),
    })

    expect(response.data).toEqual({ ok: true })
    expect(refresher).toHaveBeenCalledTimes(1)
    expect(calls).toEqual(['/projects Bearer stale-token', '/projects Bearer fresh-token'])
  })

  it('동시에 여러 요청이 401을 받아도 갱신은 한 번만 하고 모두 재시도한다', async () => {
    const refresher = vi.fn(async () => {
      await Promise.resolve()
      token = 'fresh-token'
      return 'fresh-token'
    })
    setUnauthorizedRefresher(refresher)
    const adapter = serverAccepting('fresh-token', calls)

    const results = await Promise.all([
      apiClient.get('/a', { adapter }),
      apiClient.get('/b', { adapter }),
      apiClient.get('/c', { adapter }),
    ])

    expect(results.map((r) => r.status)).toEqual([200, 200, 200])
    expect(refresher).toHaveBeenCalledTimes(1)
  })

  it('갱신 뒤에도 401이면 무한 반복하지 않고 401 오류로 끝낸다', async () => {
    const refresher = vi.fn(async () => 'still-bad-token')
    setUnauthorizedRefresher(refresher)

    const error = await apiClient
      .get('/projects', { adapter: serverAccepting('fresh-token', calls) })
      .catch((e: unknown) => e)

    expect(error).toBeInstanceOf(ApiError)
    expect((error as ApiError).status).toBe(401)
    expect(refresher).toHaveBeenCalledTimes(1)
    expect(calls).toHaveLength(2)
  })

  it('갱신 자체가 실패하면 원래의 401 오류를 그대로 돌려준다', async () => {
    const refresher = vi.fn(async () => {
      throw new ApiError({ code: 'unauthorized', message: '리프레시 만료', status: 401 })
    })
    setUnauthorizedRefresher(refresher)

    const error = await apiClient
      .get('/projects', { adapter: serverAccepting('fresh-token', calls) })
      .catch((e: unknown) => e)

    expect(error).toBeInstanceOf(ApiError)
    expect((error as ApiError).message).toBe('만료')
    expect(calls).toHaveLength(1)
  })

  it('갱신이 실패한 뒤의 다음 401은 새로 갱신을 시도한다(실패가 캐시되지 않는다)', async () => {
    let attempt = 0
    const refresher = vi.fn(async (): Promise<string> => {
      attempt += 1
      if (attempt === 1) throw new Error('network')
      token = 'fresh-token'
      return 'fresh-token'
    })
    setUnauthorizedRefresher(refresher)
    const adapter = serverAccepting('fresh-token', calls)

    await apiClient.get('/a', { adapter }).catch(() => undefined)
    const response = await apiClient.get('/b', { adapter })

    expect(response.status).toBe(200)
    expect(refresher).toHaveBeenCalledTimes(2)
  })
})

describe('응답 인터셉터: 이미 다른 요청이 갱신한 경우', () => {
  it('요청이 나간 뒤 토큰이 이미 바뀌었다면 다시 갱신하지 않고 현재 토큰으로 재시도한다', async () => {
    const refresher = vi.fn(async () => 'unused')
    setUnauthorizedRefresher(refresher)
    // 낡은 토큰으로 나간 요청이 응답을 기다리는 사이 다른 요청이 토큰을 갱신한 상황.
    const adapter: AxiosAdapter = async (config) => {
      if (config.headers.get('Authorization') === 'Bearer stale-token') token = 'fresh-token'
      return serverAccepting('fresh-token', calls)(config)
    }

    const response = await apiClient.get('/projects', { adapter })

    expect(response.status).toBe(200)
    expect(refresher).not.toHaveBeenCalled()
    expect(calls.at(-1)).toBe('/projects Bearer fresh-token')
  })
})

describe('응답 인터셉터: 갱신하지 않는 경우', () => {
  it.each(['/auth/login', '/auth/register', '/auth/refresh', '/auth/logout', '/auth/me'])(
    '%s 요청의 401은 갱신 대상이 아니다',
    async (url) => {
      const refresher = vi.fn(async () => 'fresh-token')
      setUnauthorizedRefresher(refresher)

      const error = await apiClient
        .post(url, undefined, { adapter: serverAccepting('fresh-token', calls) })
        .catch((e: unknown) => e)

      expect((error as ApiError).status).toBe(401)
      expect(refresher).not.toHaveBeenCalled()
    },
  )

  it('토큰 없이 보낸 요청(비로그인)의 401은 갱신하지 않는다', async () => {
    token = null
    const refresher = vi.fn(async () => 'fresh-token')
    setUnauthorizedRefresher(refresher)

    const error = await apiClient
      .get('/projects', { adapter: serverAccepting('fresh-token', calls) })
      .catch((e: unknown) => e)

    expect((error as ApiError).status).toBe(401)
    expect(refresher).not.toHaveBeenCalled()
  })

  it('401이 아닌 오류는 갱신하지 않는다', async () => {
    const refresher = vi.fn(async () => 'fresh-token')
    setUnauthorizedRefresher(refresher)

    const error = await apiClient
      .get('/boom', { adapter: serverAccepting('fresh-token', calls) })
      .catch((e: unknown) => e)

    expect((error as ApiError).status).toBe(500)
    expect(refresher).not.toHaveBeenCalled()
  })

  it('갱신 함수가 등록되지 않았으면 기존처럼 401 오류를 돌려준다', async () => {
    const error = await apiClient
      .get('/projects', { adapter: serverAccepting('fresh-token', calls) })
      .catch((e: unknown) => e)

    expect(error).toBeInstanceOf(ApiError)
    expect((error as ApiError).status).toBe(401)
  })
})
