import { useAuthStore } from '../stores/auth-store'
import { setUnauthorizedRefresher } from './api-client'
import { refresh } from './auth-service'

// 리프레시 토큰 쿠키로 새 액세스 토큰을 받아 스토어에 반영하고 그 토큰을 돌려준다.
// 실패하면 세션을 비우고(→ ProtectedRoute가 로그인 화면으로 보낸다) 오류를 다시 던진다.
export async function refreshSession(): Promise<string> {
  try {
    const { accessToken, expiresIn } = await refresh()
    // 갱신 응답을 기다리는 사이 로그아웃됐다면 사용자 정보 없는 토큰으로 세션을 되살리지 않는다.
    if (useAuthStore.getState().accessToken === null) {
      throw new Error('갱신 중에 로그아웃되었습니다.')
    }
    useAuthStore.getState().setAccessToken(accessToken, expiresIn)
    return accessToken
  } catch (error) {
    useAuthStore.getState().clearSession()
    throw error
  }
}

// api-client의 401 응답 처리(요청 재시도)가 이 함수를 쓰도록 등록한다. store가 로드될 때
// 토큰 공급자를 등록하는 auth-store와 같은 방식이다(api-client는 store를 import하지 않는다).
setUnauthorizedRefresher(refreshSession)
