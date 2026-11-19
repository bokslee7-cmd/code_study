import { useCallback, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { fetchMe, logout as requestLogout, refresh } from '../services/auth-service'
import { refreshSession } from '../services/session-refresh'
import { selectIsAuthenticated, useAuthStore } from '../stores/auth-store'

// 만료 직전(이 시간만큼 앞서) 새 액세스 토큰을 받아 요청 도중 만료되는 일을 피한다.
const REFRESH_MARGIN_MS = 60_000

async function restoreSession(): Promise<void> {
  const { setSession, clearSession, finishRestoring } = useAuthStore.getState()
  try {
    const { accessToken, expiresIn } = await refresh()
    const user = await fetchMe(accessToken)
    setSession({ accessToken, user, expiresIn })
  } catch {
    clearSession()
  } finally {
    finishRestoring()
  }
}

// 실패 시 세션 정리는 refreshSession이 이미 했으므로 여기서는 오류를 흘려보낸다.
function refreshAccessToken(): void {
  refreshSession().catch(() => undefined)
}

// 앱 최상단에서 한 번만 호출한다: 시작 시 세션 복구 + 만료 직전 자동 토큰 갱신.
export function useAuthSession(): void {
  const tokenExpiresAt = useAuthStore((state) => state.tokenExpiresAt)
  // StrictMode가 effect를 두 번 실행해도 리프레시 토큰이 두 번 소모되지 않게 한다.
  const hasStartedRestore = useRef(false)

  useEffect(() => {
    if (hasStartedRestore.current) return
    hasStartedRestore.current = true
    void restoreSession()
  }, [])

  useEffect(() => {
    if (tokenExpiresAt === null) return
    const delay = Math.max(tokenExpiresAt - Date.now() - REFRESH_MARGIN_MS, 0)
    const timerId = setTimeout(refreshAccessToken, delay)
    return () => clearTimeout(timerId)
  }, [tokenExpiresAt])
}

export function useAuth() {
  const navigate = useNavigate()
  const user = useAuthStore((state) => state.user)
  const isAuthenticated = useAuthStore(selectIsAuthenticated)

  // 서버 요청이 실패해도 로컬 세션은 반드시 정리한다.
  const logout = useCallback(async () => {
    try {
      await requestLogout()
    } catch {
      // 서버 로그아웃 실패는 사용자에게 의미가 없다. 아래에서 로컬 세션을 지운다.
    } finally {
      useAuthStore.getState().clearSession()
      navigate('/login', { replace: true })
    }
  }, [navigate])

  return { user, isAuthenticated, logout }
}
