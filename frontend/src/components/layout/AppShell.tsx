import { Outlet } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { useAuth } from '../../hooks/useAuth'

// 로그인한 사용자 화면의 공통 틀: 상단에 사용자 정보와 로그아웃 버튼, 아래에 각 페이지.
export default function AppShell() {
  const { user, logout } = useAuth()

  return (
    <>
      <header className="flex items-center justify-end gap-3 border-b px-4 py-2 text-sm">
        {user && <span>{user.email}</span>}
        <Button variant="outline" size="sm" onClick={() => void logout()}>
          로그아웃
        </Button>
      </header>
      <Outlet />
    </>
  )
}
