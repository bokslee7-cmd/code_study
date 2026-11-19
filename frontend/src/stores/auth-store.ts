import { create } from 'zustand'
import { setAuthTokenProvider } from '../services/api-client'

export interface AuthUser {
  id: string
  email: string
  skillLevel: string
}

interface AuthSession {
  accessToken: string
  user: AuthUser
  // 서버가 알려준 액세스 토큰 유효 시간(초). 자동 갱신 시점을 계산하는 데 쓴다.
  expiresIn?: number
}

interface AuthState {
  accessToken: string | null
  user: AuthUser | null
  // 액세스 토큰이 만료되는 시각(ms, epoch). expiresIn을 모르면 null.
  tokenExpiresAt: number | null
  // 앱 시작 시 쿠키의 리프레시 토큰으로 세션을 복구하는 동안 true.
  isRestoring: boolean
  setSession: (session: AuthSession) => void
  setAccessToken: (accessToken: string, expiresIn?: number) => void
  clearSession: () => void
  finishRestoring: () => void
}

const toExpiresAt = (expiresIn?: number): number | null =>
  expiresIn === undefined ? null : Date.now() + expiresIn * 1000

// 액세스 토큰은 메모리에만 둔다. localStorage에 두면 XSS로 읽힐 수 있고,
// 새로고침 후 복구는 HttpOnly 쿠키의 리프레시 토큰(T038)이 맡는다.
export const useAuthStore = create<AuthState>()((set) => ({
  accessToken: null,
  user: null,
  tokenExpiresAt: null,
  isRestoring: true,
  setSession: ({ accessToken, user, expiresIn }) =>
    set({ accessToken, user, tokenExpiresAt: toExpiresAt(expiresIn) }),
  setAccessToken: (accessToken, expiresIn) =>
    set({ accessToken, tokenExpiresAt: toExpiresAt(expiresIn) }),
  clearSession: () => set({ accessToken: null, user: null, tokenExpiresAt: null }),
  finishRestoring: () => set({ isRestoring: false }),
}))

export const selectIsAuthenticated = (state: AuthState): boolean => state.accessToken !== null

// api-client가 store를 import하면 순환 의존이 되므로, store 쪽에서 토큰 공급자를 등록한다.
setAuthTokenProvider(() => useAuthStore.getState().accessToken)
