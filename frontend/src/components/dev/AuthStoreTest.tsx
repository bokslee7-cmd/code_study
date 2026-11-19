import { Button } from '@/components/ui/button'
import { selectIsAuthenticated, useAuthStore, type AuthUser } from '../../stores/auth-store'

const TEST_USER: AuthUser = {
  id: 'dev-user-1',
  email: 'dev-test@example.com',
  skillLevel: 'Complete Beginner',
}
// 개발 화면 확인용 가짜 토큰이다. 실제 서버가 발급한 값이 아니다.
const TEST_ACCESS_TOKEN = 'dev-test-token'

function UserDisplay() {
  const user = useAuthStore((state) => state.user)

  return (
    <section aria-label="사용자 정보">
      <h3>user</h3>
      {user ? <pre>{JSON.stringify(user, null, 2)}</pre> : <p>사용자 없음</p>}
    </section>
  )
}

function AuthStatusDisplay() {
  const isAuthenticated = useAuthStore(selectIsAuthenticated)

  return (
    <section aria-label="인증 상태">
      <h3>isAuthenticated</h3>
      <p>isAuthenticated: {String(isAuthenticated)}</p>
    </section>
  )
}

// 같은 스토어를 각각 구독하는 두 컴포넌트가 버튼 한 번에 함께 갱신되는지 확인하는 개발용 영역.
export default function AuthStoreTest() {
  const setSession = useAuthStore((state) => state.setSession)
  const clearSession = useAuthStore((state) => state.clearSession)

  return (
    <section aria-label="인증 스토어 테스트">
      <h2>인증 스토어 테스트</h2>
      <Button
        type="button"
        onClick={() => setSession({ accessToken: TEST_ACCESS_TOKEN, user: TEST_USER })}
      >
        사용자 설정
      </Button>
      <Button type="button" variant="outline" onClick={clearSession}>
        인증 초기화
      </Button>
      <UserDisplay />
      <AuthStatusDisplay />
    </section>
  )
}
