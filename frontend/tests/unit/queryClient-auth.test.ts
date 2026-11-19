import { queryClient } from '../../src/lib/queryClient'
import { useAuthStore } from '../../src/stores/auth-store'

const user = { id: 'u-1', email: 'learner@example.com', skillLevel: 'Complete Beginner' }

afterEach(() => {
  useAuthStore.getState().clearSession()
  queryClient.clear()
})

describe('로그아웃/세션 종료 시 서버 데이터 캐시 정리', () => {
  it('세션이 사라지면 캐시된 서버 데이터를 모두 지워 다음 사용자에게 보이지 않게 한다', () => {
    useAuthStore.getState().setSession({ accessToken: 'access-1', user, expiresIn: 900 })
    queryClient.setQueryData(['projects'], [{ id: 'p-1' }])

    useAuthStore.getState().clearSession()

    expect(queryClient.getQueryData(['projects'])).toBeUndefined()
  })

  it('토큰을 갱신하는 동안에는 캐시를 지우지 않는다', () => {
    useAuthStore.getState().setSession({ accessToken: 'access-1', user, expiresIn: 900 })
    queryClient.setQueryData(['projects'], [{ id: 'p-1' }])

    useAuthStore.getState().setAccessToken('access-2', 900)

    expect(queryClient.getQueryData(['projects'])).toEqual([{ id: 'p-1' }])
  })
})
