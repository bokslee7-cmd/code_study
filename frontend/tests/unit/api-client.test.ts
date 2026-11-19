import axios, { AxiosError, type AxiosAdapter } from 'axios'
import { shouldRetry } from '../../src/lib/queryClient'
import {
  ApiError,
  apiClient,
  setAuthTokenProvider,
  toApiError,
} from '../../src/services/api-client'

function adapterReturning(status: number, data: unknown, onRequest?: (c: unknown) => void) {
  const adapter: AxiosAdapter = async (config) => {
    onRequest?.(config)
    const response = { data, status, statusText: '', headers: {}, config }
    if (status >= 200 && status < 300) return response
    throw new AxiosError('failed', AxiosError.ERR_BAD_RESPONSE, config, null, response)
  }
  return adapter
}

function adapterFailing(code: string, message: string) {
  const adapter: AxiosAdapter = async (config) => {
    throw new AxiosError(message, code, config)
  }
  return adapter
}

async function catchError(promise: Promise<unknown>): Promise<unknown> {
  try {
    await promise
  } catch (error) {
    return error
  }
  throw new Error('요청이 실패해야 하지만 성공했다')
}

afterEach(() => {
  setAuthTokenProvider(null)
  vi.unstubAllEnvs()
  vi.resetModules()
})

describe('apiClient 기본 설정', () => {
  it('VITE_API_BASE_URL이 없으면 로컬 백엔드 /api/v1을 기본 주소로 쓴다', async () => {
    vi.stubEnv('VITE_API_BASE_URL', '')
    vi.resetModules()
    const { apiClient: client } = await import('../../src/services/api-client')

    expect(client.defaults.baseURL).toBe('http://localhost:8000/api/v1')
  })

  it('VITE_API_BASE_URL 환경 변수를 기본 주소로 쓴다', async () => {
    vi.stubEnv('VITE_API_BASE_URL', 'https://api.example.com/api/v1')
    vi.resetModules()
    const { apiClient: client } = await import('../../src/services/api-client')

    expect(client.defaults.baseURL).toBe('https://api.example.com/api/v1')
  })

  it('10초 타임아웃을 설정한다', () => {
    expect(apiClient.defaults.timeout).toBe(10_000)
  })
})

describe('요청 인터셉터: 인증 헤더', () => {
  it('토큰 공급자가 토큰을 주면 Authorization: Bearer 헤더를 붙인다', async () => {
    setAuthTokenProvider(() => 'access-token')
    let sent: { headers: { get(name: string): unknown } } | undefined

    await apiClient.get('/projects', {
      adapter: adapterReturning(200, {}, (config) => {
        sent = config as typeof sent
      }),
    })

    expect(sent?.headers.get('Authorization')).toBe('Bearer access-token')
  })

  it('토큰이 null이면 Authorization 헤더를 붙이지 않는다', async () => {
    setAuthTokenProvider(() => null)
    let sent: { headers: { get(name: string): unknown } } | undefined

    await apiClient.get('/projects', {
      adapter: adapterReturning(200, {}, (config) => {
        sent = config as typeof sent
      }),
    })

    expect(sent?.headers.get('Authorization')).toBeFalsy()
  })

  it('토큰 공급자를 등록하지 않으면 Authorization 헤더를 붙이지 않는다', async () => {
    let sent: { headers: { get(name: string): unknown } } | undefined

    await apiClient.get('/projects', {
      adapter: adapterReturning(200, {}, (config) => {
        sent = config as typeof sent
      }),
    })

    expect(sent?.headers.get('Authorization')).toBeFalsy()
  })
})

describe('응답 처리', () => {
  it('성공 응답은 데이터를 그대로 돌려준다', async () => {
    const response = await apiClient.get('/projects', {
      adapter: adapterReturning(200, { items: [] }),
    })

    expect(response.data).toEqual({ items: [] })
  })

  it('백엔드 ErrorResponse를 ApiError로 변환한다', async () => {
    const body = {
      error: 'not_found',
      message: '프로젝트를 찾을 수 없습니다.',
      suggestion: '목록에서 다시 선택하세요.',
    }

    const error = await catchError(
      apiClient.get('/projects/1', { adapter: adapterReturning(404, body) }),
    )

    expect(error).toBeInstanceOf(ApiError)
    expect(error).toMatchObject({
      status: 404,
      code: 'not_found',
      message: '프로젝트를 찾을 수 없습니다.',
      suggestion: '목록에서 다시 선택하세요.',
    })
  })

  it('검증 오류의 details를 보존한다', async () => {
    const details = { errors: [{ field: 'body.email', message: 'field required' }] }
    const body = { error: 'validation_error', message: '입력값이 올바르지 않습니다.', details }

    const error = await catchError(
      apiClient.post('/auth/register', {}, { adapter: adapterReturning(400, body) }),
    )

    expect(error).toMatchObject({ status: 400, code: 'validation_error', details })
  })

  it('ErrorResponse 형식이 아닌 응답은 상태 코드 기반의 일반 오류로 변환한다', async () => {
    const error = await catchError(
      apiClient.get('/projects', { adapter: adapterReturning(502, '<html>Bad Gateway</html>') }),
    )

    expect(error).toBeInstanceOf(ApiError)
    expect(error).toMatchObject({ status: 502, code: 'unknown_error' })
    expect((error as ApiError).message).not.toContain('<html>')
  })

  it('서버에 연결하지 못하면 network_error로 변환한다', async () => {
    const error = await catchError(
      apiClient.get('/projects', {
        adapter: adapterFailing(AxiosError.ERR_NETWORK, 'Network Error'),
      }),
    )

    expect(error).toBeInstanceOf(ApiError)
    expect(error).toMatchObject({ status: undefined, code: 'network_error' })
    expect((error as ApiError).message).toContain('네트워크')
  })

  it('시간이 초과되면 timeout으로 변환한다', async () => {
    const error = await catchError(
      apiClient.get('/projects', {
        adapter: adapterFailing(AxiosError.ECONNABORTED, 'timeout of 10000ms exceeded'),
      }),
    )

    expect(error).toMatchObject({ code: 'timeout' })
    expect((error as ApiError).message).toContain('시간')
  })

  it('응답이 없는 기타 axios 오류는 unknown_error로 변환한다', async () => {
    const error = await catchError(
      apiClient.get('/projects', {
        adapter: adapterFailing(AxiosError.ERR_BAD_OPTION, 'bad option'),
      }),
    )

    expect(error).toMatchObject({ status: undefined, code: 'unknown_error' })
  })

  it('취소된 요청은 ApiError로 바꾸지 않고 그대로 던진다', async () => {
    const adapter: AxiosAdapter = async () => {
      throw new axios.CanceledError('canceled')
    }

    const error = await catchError(apiClient.get('/projects', { adapter }))

    expect(axios.isCancel(error)).toBe(true)
  })
})

describe('toApiError', () => {
  it('이미 ApiError이면 같은 객체를 돌려준다', () => {
    const apiError = new ApiError({ code: 'forbidden', message: '권한 없음', status: 403 })

    expect(toApiError(apiError)).toBe(apiError)
  })

  it('axios 오류가 아닌 값은 unknown_error로 변환한다', () => {
    expect(toApiError(new Error('boom'))).toMatchObject({ code: 'unknown_error' })
    expect(toApiError(null)).toMatchObject({ code: 'unknown_error' })
  })
})

describe('TanStack Query 재시도 정책과의 연동', () => {
  it('4xx ApiError는 재시도하지 않는다', () => {
    const error = new ApiError({ code: 'not_found', message: '없음', status: 404 })

    expect(shouldRetry(0, error)).toBe(false)
  })

  it('5xx ApiError와 network_error는 재시도한다', () => {
    const serverError = new ApiError({ code: 'server_error', message: '오류', status: 500 })
    const networkError = new ApiError({ code: 'network_error', message: '연결 실패' })

    expect(shouldRetry(0, serverError)).toBe(true)
    expect(shouldRetry(0, networkError)).toBe(true)
  })
})
