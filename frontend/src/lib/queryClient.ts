import { QueryClient } from '@tanstack/react-query'
import { useAuthStore } from '../stores/auth-store'

const MAX_RETRIES = 2
const STALE_TIME_MS = 30_000

// 4xx는 같은 요청을 반복해도 결과가 같으므로 재시도하지 않는다.
export function shouldRetry(failureCount: number, error: unknown): boolean {
  const status = (error as { response?: { status?: number } } | null)?.response?.status
  if (status !== undefined && status >= 400 && status < 500) {
    return false
  }
  return failureCount < MAX_RETRIES
}

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: STALE_TIME_MS,
      retry: shouldRetry,
      refetchOnWindowFocus: false,
    },
    mutations: {
      retry: false,
    },
  },
})

// 로그아웃·세션 만료로 토큰이 사라지면 캐시된 서버 데이터도 지운다.
// 지우지 않으면 같은 브라우저로 다른 계정이 로그인했을 때 이전 사용자의 프로젝트가 잠깐 보인다.
useAuthStore.subscribe((state, previous) => {
  if (previous.accessToken !== null && state.accessToken === null) queryClient.clear()
})
