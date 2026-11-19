import { ApiError, apiClient } from '../../src/services/api-client'
import { fetchMe, login, logout, refresh, register } from '../../src/services/auth-service'

const serverUser = { id: 'u-1', email: 'learner@example.com', skill_level: 'Intermediate' }
const appUser = { id: 'u-1', email: 'learner@example.com', skillLevel: 'Intermediate' }
const credentials = { email: 'learner@example.com', password: 'password123' }

afterEach(() => {
  vi.restoreAllMocks()
})

describe('register', () => {
  it('POST /auth/register에 이메일과 비밀번호를 보내고 camelCase 사용자로 변환해 돌려준다', async () => {
    const post = vi.spyOn(apiClient, 'post').mockResolvedValue({ data: { user: serverUser } })

    const user = await register(credentials)

    expect(post).toHaveBeenCalledWith('/auth/register', credentials)
    expect(user).toEqual(appUser)
  })

  it('skill_level이 null이면 기본 수준(Complete Beginner)으로 채운다', async () => {
    vi.spyOn(apiClient, 'post').mockResolvedValue({
      data: { user: { ...serverUser, skill_level: null } },
    })

    const user = await register(credentials)

    expect(user.skillLevel).toBe('Complete Beginner')
  })

  it('서버 오류(ApiError)는 그대로 던진다', async () => {
    const error = new ApiError({
      code: 'conflict',
      message: '이미 가입된 이메일입니다.',
      status: 409,
    })
    vi.spyOn(apiClient, 'post').mockRejectedValue(error)

    await expect(register(credentials)).rejects.toBe(error)
  })
})

describe('login', () => {
  it('쿠키를 주고받도록 withCredentials와 함께 POST /auth/login을 호출한다', async () => {
    const post = vi.spyOn(apiClient, 'post').mockResolvedValue({
      data: { access_token: 'access-1', token_type: 'bearer', expires_in: 900, user: serverUser },
    })

    const result = await login(credentials)

    expect(post).toHaveBeenCalledWith('/auth/login', credentials, { withCredentials: true })
    expect(result).toEqual({ accessToken: 'access-1', expiresIn: 900, user: appUser })
  })

  it('401 같은 서버 오류는 그대로 던진다', async () => {
    const error = new ApiError({ code: 'unauthorized', message: '인증 실패', status: 401 })
    vi.spyOn(apiClient, 'post').mockRejectedValue(error)

    await expect(login(credentials)).rejects.toBe(error)
  })
})

describe('logout', () => {
  it('바디 없이 withCredentials와 함께 POST /auth/logout을 호출한다', async () => {
    const post = vi.spyOn(apiClient, 'post').mockResolvedValue({ data: undefined })

    await expect(logout()).resolves.toBeUndefined()

    expect(post).toHaveBeenCalledWith('/auth/logout', undefined, { withCredentials: true })
  })
})

describe('refresh', () => {
  it('바디 없이 withCredentials와 함께 POST /auth/refresh를 호출하고 새 토큰을 돌려준다', async () => {
    const post = vi.spyOn(apiClient, 'post').mockResolvedValue({
      data: { access_token: 'access-2', token_type: 'bearer', expires_in: 900 },
    })

    const result = await refresh()

    expect(post).toHaveBeenCalledWith('/auth/refresh', undefined, { withCredentials: true })
    expect(result).toEqual({ accessToken: 'access-2', expiresIn: 900 })
  })
})

describe('fetchMe', () => {
  it('넘겨받은 토큰을 Authorization 헤더로 GET /auth/me를 호출하고 사용자를 변환한다', async () => {
    const get = vi.spyOn(apiClient, 'get').mockResolvedValue({ data: serverUser })

    const user = await fetchMe('access-9')

    expect(get).toHaveBeenCalledWith('/auth/me', {
      headers: { Authorization: 'Bearer access-9' },
    })
    expect(user).toEqual(appUser)
  })
})
