import axios, { type InternalAxiosRequestConfig } from 'axios'

const DEFAULT_BASE_URL = 'http://localhost:8000/api/v1'
const REQUEST_TIMEOUT_MS = 10_000

const NETWORK_ERROR_MESSAGE =
  '서버에 연결할 수 없습니다. 네트워크 연결을 확인한 뒤 다시 시도하세요.'
const TIMEOUT_ERROR_MESSAGE = '응답 시간이 초과되었습니다. 잠시 후 다시 시도하세요.'
const UNKNOWN_ERROR_MESSAGE = '요청을 처리하지 못했습니다. 잠시 후 다시 시도하세요.'

export type AuthTokenProvider = () => string | null

// auth-store가 로드될 때 토큰 조회 함수를 등록한다. 순환 import를 피하려고 주입 방식을 쓴다.
let getAuthToken: AuthTokenProvider | null = null

export function setAuthTokenProvider(provider: AuthTokenProvider | null): void {
  getAuthToken = provider
}

interface ApiErrorInit {
  code: string
  message: string
  status?: number
  details?: Record<string, unknown>
  suggestion?: string
}

// 백엔드 ErrorResponse(error, message, details, suggestion)를 화면에서 다루기 쉬운 형태로 옮긴 오류.
export class ApiError extends Error {
  readonly code: string
  readonly status: number | undefined
  readonly details: Record<string, unknown> | undefined
  readonly suggestion: string | undefined
  // TanStack Query의 shouldRetry가 읽는 axios 오류 형태(response.status)와 맞춘다.
  readonly response: { status: number } | undefined

  constructor({ code, message, status, details, suggestion }: ApiErrorInit) {
    super(message)
    this.name = 'ApiError'
    this.code = code
    this.status = status
    this.details = details
    this.suggestion = suggestion
    this.response = status === undefined ? undefined : { status }
  }
}

interface ErrorBody {
  error: string
  message: string
  details?: Record<string, unknown>
  suggestion?: string
}

function isErrorBody(data: unknown): data is ErrorBody {
  if (typeof data !== 'object' || data === null) return false
  const body = data as Record<string, unknown>
  return typeof body.error === 'string' && typeof body.message === 'string'
}

const TIMEOUT_CODES = new Set<string>([axios.AxiosError.ECONNABORTED, axios.AxiosError.ETIMEDOUT])

export function toApiError(error: unknown): ApiError {
  if (error instanceof ApiError) return error

  if (!axios.isAxiosError(error)) {
    return new ApiError({ code: 'unknown_error', message: UNKNOWN_ERROR_MESSAGE })
  }

  if (error.response) {
    const { status, data } = error.response
    if (isErrorBody(data)) {
      return new ApiError({
        code: data.error,
        message: data.message,
        status,
        details: data.details,
        suggestion: data.suggestion,
      })
    }
    return new ApiError({ code: 'unknown_error', message: UNKNOWN_ERROR_MESSAGE, status })
  }

  if (error.code !== undefined && TIMEOUT_CODES.has(error.code)) {
    return new ApiError({ code: 'timeout', message: TIMEOUT_ERROR_MESSAGE })
  }
  if (error.code === axios.AxiosError.ERR_NETWORK) {
    return new ApiError({ code: 'network_error', message: NETWORK_ERROR_MESSAGE })
  }
  return new ApiError({ code: 'unknown_error', message: UNKNOWN_ERROR_MESSAGE })
}

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || DEFAULT_BASE_URL,
  timeout: REQUEST_TIMEOUT_MS,
})

apiClient.interceptors.request.use((config) => {
  const token = getAuthToken?.()
  if (token) {
    config.headers.set('Authorization', `Bearer ${token}`)
  }
  return config
})

// 401을 받았을 때 새 액세스 토큰을 받아 돌려주는 함수. 스토어/auth-service에 의존하므로
// 순환 import를 피하려고 session-refresh가 등록한다. 등록 전이면 401은 그대로 오류가 된다.
export type UnauthorizedRefresher = () => Promise<string>

declare module 'axios' {
  interface AxiosRequestConfig {
    // 401 갱신 뒤 다시 보낸 요청 표시. 같은 요청을 두 번 이상 재시도하지 않기 위해 쓴다.
    _authRetried?: boolean
  }
}

let refreshAccessToken: UnauthorizedRefresher | null = null
let inFlightRefresh: Promise<string> | null = null

export function setUnauthorizedRefresher(refresher: UnauthorizedRefresher | null): void {
  refreshAccessToken = refresher
  inFlightRefresh = null
}

// 동시에 여러 요청이 401을 받아도 갱신 요청은 하나만 보낸다(리프레시 토큰은 1회용이기 때문).
function refreshOnce(refresher: UnauthorizedRefresher): Promise<string> {
  inFlightRefresh ??= refresher().finally(() => {
    inFlightRefresh = null
  })
  return inFlightRefresh
}

// 로그인·갱신 같은 인증 요청의 401은 "토큰 만료"가 아니라 그 자체가 결과이므로 갱신하지 않는다.
const AUTH_PATH_PREFIX = '/auth/'

function isRefreshable(error: ApiError, config: InternalAxiosRequestConfig): boolean {
  return (
    error.status === 401 &&
    config._authRetried !== true &&
    !config.url?.startsWith(AUTH_PATH_PREFIX) &&
    Boolean(config.headers.get('Authorization'))
  )
}

// 새 토큰을 구한다. 이 요청이 나간 뒤 다른 요청이 이미 토큰을 갱신했다면 다시 갱신하지 않고
// 현재 토큰을 쓴다. 갱신이 실패하면 null(호출 쪽이 원래의 401을 돌려준다).
async function obtainFreshToken(
  sentAuthorization: string,
  refresher: UnauthorizedRefresher,
): Promise<string | null> {
  const currentToken = getAuthToken?.()
  if (currentToken && `Bearer ${currentToken}` !== sentAuthorization) return currentToken
  try {
    return await refreshOnce(refresher)
  } catch {
    return null
  }
}

apiClient.interceptors.response.use(
  (response) => response,
  async (error: unknown) => {
    // 취소(AbortController)는 오류가 아니므로 TanStack Query가 구분할 수 있게 그대로 둔다.
    if (axios.isCancel(error)) throw error
    const apiError = toApiError(error)
    const config = axios.isAxiosError(error) ? error.config : undefined
    const refresher = refreshAccessToken
    if (!config || !refresher || !isRefreshable(apiError, config)) throw apiError

    const freshToken = await obtainFreshToken(
      String(config.headers.get('Authorization')),
      refresher,
    )
    if (freshToken === null) throw apiError

    // 다시 보낸 요청이 또 401이어도 _authRetried 때문에 여기서 끝나고 반복되지 않는다.
    config.headers.set('Authorization', `Bearer ${freshToken}`)
    return apiClient.request({ ...config, _authRetried: true })
  },
)
