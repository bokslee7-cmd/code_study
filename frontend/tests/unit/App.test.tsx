import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import App from '../../src/App'
import { fetchMe, refresh } from '../../src/services/auth-service'
import { getProject, listProjects } from '../../src/services/project-service'
import { getTask, listTasks } from '../../src/services/task-service'
import { useAuthStore } from '../../src/stores/auth-store'
import { makeProject } from '../fixtures/project'
import { makeTask } from '../fixtures/task'

// T037 이후 대시보드·프로젝트·휴지통 경로는 로그인이 필요하다. 이 파일은 "경로 → 페이지" 연결만
// 확인하므로 로그인된 세션을 미리 심고, 시작 시 세션 복구(refresh → me)도 성공하도록 mock 한다.
// (비로그인 시 보호·리다이렉트 동작은 App-auth.test.tsx가 검증한다.)
// T054/T055 이후 대시보드·프로젝트 상세는 서버 데이터를 불러오므로 프로젝트 서비스도 mock 하고
// QueryClientProvider로 감싼다. 두 페이지는 데이터를 불러온 뒤 그려지므로 해당 단언은 비동기(findBy)다.
vi.mock('../../src/services/auth-service')
vi.mock('../../src/services/project-service')
vi.mock('../../src/services/task-service')

const session = {
  accessToken: 'test-access-token',
  user: { id: 'u-1', email: 'learner@example.com', skillLevel: 'Complete Beginner' },
  expiresIn: 900,
}

beforeEach(() => {
  vi.mocked(refresh).mockResolvedValue({ accessToken: session.accessToken, expiresIn: 900 })
  vi.mocked(fetchMe).mockResolvedValue(session.user)
  vi.mocked(listProjects).mockResolvedValue([])
  vi.mocked(getProject).mockResolvedValue(makeProject({ id: 'p1' }))
  vi.mocked(listTasks).mockResolvedValue([])
  vi.mocked(getTask).mockResolvedValue(makeTask({ id: 't1', projectId: 'p1' }))
  useAuthStore.getState().setSession(session)
  useAuthStore.setState({ isRestoring: false })
})

afterEach(() => {
  vi.resetAllMocks()
  useAuthStore.getState().clearSession()
  useAuthStore.setState({ isRestoring: true })
})

function renderAt(path: string) {
  return render(
    <QueryClientProvider
      client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
    >
      <MemoryRouter initialEntries={[path]}>
        <App />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('App 라우팅', () => {
  it.each([
    ['/login', '로그인'],
    ['/register', '회원가입'],
    ['/dashboard', '대시보드'],
    ['/projects/p1', 'My Todo App'],
    ['/projects/p1/tasks/t1', 'Add Todo Function'],
    ['/trash', '휴지통'],
  ])('%s 경로는 "%s" 페이지를 렌더링한다', async (path, heading) => {
    renderAt(path)
    expect(await screen.findByRole('heading', { name: heading })).toBeInTheDocument()
  })

  it('/dashboard 경로는 프로젝트 목록 화면(빈 상태 포함)을 보여준다', async () => {
    renderAt('/dashboard')
    expect(await screen.findByText('아직 프로젝트가 없습니다.')).toBeInTheDocument()
  })

  it('루트(/) 경로는 대시보드로 이동한다', async () => {
    renderAt('/')
    expect(await screen.findByRole('heading', { name: '대시보드' })).toBeInTheDocument()
  })

  it('정의되지 않은 경로는 404 페이지를 렌더링한다', () => {
    renderAt('/does-not-exist')
    expect(screen.getByRole('heading', { name: '페이지를 찾을 수 없습니다' })).toBeInTheDocument()
  })

  it('404 페이지에서 대시보드로 돌아가는 링크를 제공한다', () => {
    renderAt('/does-not-exist')
    expect(screen.getByRole('link', { name: '대시보드로 돌아가기' })).toHaveAttribute(
      'href',
      '/dashboard',
    )
  })

  it('프로젝트 하위 경로가 아닌 잘못된 형태는 404로 처리한다', () => {
    renderAt('/projects/p1/unknown')
    expect(screen.getByRole('heading', { name: '페이지를 찾을 수 없습니다' })).toBeInTheDocument()
  })
})
