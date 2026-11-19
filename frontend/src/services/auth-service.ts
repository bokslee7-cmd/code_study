import type { AuthUser } from '../stores/auth-store'
import { apiClient } from './api-client'

// 서버가 skill_level을 아직 정하지 않았을 때 쓰는 기본값(spec.md: default Complete Beginner).
const DEFAULT_SKILL_LEVEL = 'Complete Beginner'

// 리프레시 토큰 쿠키(HttpOnly)를 주고받는 요청에만 붙인다.
const WITH_CREDENTIALS = { withCredentials: true } as const

export interface Credentials {
  email: string
  password: string
}

export interface TokenResult {
  accessToken: string
  expiresIn: number
}

export interface LoginResult extends TokenResult {
  user: AuthUser
}

interface UserDto {
  id: string
  email: string
  skill_level: string | null
}

interface TokenDto {
  access_token: string
  expires_in: number
}

interface LoginDto extends TokenDto {
  user: UserDto
}

function toAuthUser(dto: UserDto): AuthUser {
  return { id: dto.id, email: dto.email, skillLevel: dto.skill_level ?? DEFAULT_SKILL_LEVEL }
}

function toTokenResult(dto: TokenDto): TokenResult {
  return { accessToken: dto.access_token, expiresIn: dto.expires_in }
}

export async function register(credentials: Credentials): Promise<AuthUser> {
  const { data } = await apiClient.post<{ user: UserDto }>('/auth/register', credentials)
  return toAuthUser(data.user)
}

export async function login(credentials: Credentials): Promise<LoginResult> {
  const { data } = await apiClient.post<LoginDto>('/auth/login', credentials, WITH_CREDENTIALS)
  return { ...toTokenResult(data), user: toAuthUser(data.user) }
}

export async function logout(): Promise<void> {
  await apiClient.post('/auth/logout', undefined, WITH_CREDENTIALS)
}

export async function refresh(): Promise<TokenResult> {
  const { data } = await apiClient.post<TokenDto>('/auth/refresh', undefined, WITH_CREDENTIALS)
  return toTokenResult(data)
}

// 세션 복구 중에는 아직 스토어에 토큰이 없으므로 방금 받은 토큰을 직접 넘긴다.
export async function fetchMe(accessToken: string): Promise<AuthUser> {
  const { data } = await apiClient.get<UserDto>('/auth/me', {
    headers: { Authorization: `Bearer ${accessToken}` },
  })
  return toAuthUser(data)
}
