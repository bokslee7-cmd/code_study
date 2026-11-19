import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { selectIsAuthenticated, useAuthStore } from '../../stores/auth-store'

// 하위 라우트를 로그인한 사용자에게만 보여준다. 세션 복구 중에는 판단을 미뤄서
// 새로고침 때 로그인 페이지로 잘못 튕겼다가 돌아오는 깜빡임을 막는다.
export default function ProtectedRoute() {
  const isAuthenticated = useAuthStore(selectIsAuthenticated)
  const isRestoring = useAuthStore((state) => state.isRestoring)
  const location = useLocation()

  if (isAuthenticated) return <Outlet />
  if (isRestoring) return <p role="status">로그인 상태를 확인하는 중입니다...</p>
  return <Navigate to="/login" replace state={{ from: location }} />
}
