import { Link, Navigate, Route, Routes } from 'react-router-dom'
import ProtectedRoute from './components/auth/ProtectedRoute'
import AppShell from './components/layout/AppShell'
import { useAuthSession } from './hooks/useAuth'
import Dashboard from './pages/Dashboard'
import DevTestPage from './pages/DevTestPage'
import Login from './pages/Login'
import ProjectDetail from './pages/ProjectDetail'
import Register from './pages/Register'
import TaskDetail from './pages/TaskDetail'

// 실제 페이지가 구현되면 각 Route의 element를 해당 페이지로 교체한다.
function PagePlaceholder({ title }: { title: string }) {
  return (
    <main>
      <h1>{title}</h1>
    </main>
  )
}

function NotFound() {
  return (
    <main>
      <h1>페이지를 찾을 수 없습니다</h1>
      <Link to="/dashboard">대시보드로 돌아가기</Link>
    </main>
  )
}

export default function App() {
  useAuthSession()

  return (
    <Routes>
      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route element={<ProtectedRoute />}>
        <Route element={<AppShell />}>
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/projects/:projectId" element={<ProjectDetail />} />
          <Route path="/projects/:projectId/tasks/:taskId" element={<TaskDetail />} />
          <Route path="/trash" element={<PagePlaceholder title="휴지통" />} />
        </Route>
      </Route>
      <Route path="/dev-test" element={<DevTestPage />} />
      <Route path="*" element={<NotFound />} />
    </Routes>
  )
}
