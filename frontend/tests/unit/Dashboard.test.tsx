import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import Dashboard from '../../src/pages/Dashboard'
import { ApiError } from '../../src/services/api-client'
import { createProject, listProjects } from '../../src/services/project-service'
import { makeProject } from '../fixtures/project'

vi.mock('../../src/services/project-service')

function renderDashboard() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <Dashboard />
      </MemoryRouter>
    </QueryClientProvider>,
  )
  return queryClient
}

afterEach(() => {
  vi.resetAllMocks()
})

describe('Dashboard 목록', () => {
  it('"대시보드" 제목과 프로젝트 카드(제목·진행 상황)를 서버가 준 순서대로 보여준다', async () => {
    vi.mocked(listProjects).mockResolvedValue([
      makeProject({ id: 'p-1', title: '최근 프로젝트', taskCount: 5, completedTaskCount: 2 }),
      makeProject({ id: 'p-2', title: '오래된 프로젝트' }),
    ])

    renderDashboard()

    expect(screen.getByRole('heading', { level: 1, name: '대시보드' })).toBeInTheDocument()
    const links = await screen.findAllByRole('link')
    expect(links.map((link) => link.textContent)).toEqual(['최근 프로젝트', '오래된 프로젝트'])
    expect(screen.getByText('2/5 태스크 완료')).toBeInTheDocument()
    expect(screen.getByText('0/0 태스크 완료')).toBeInTheDocument()
  })

  it('목록 쿼리 키는 ["projects"]다', async () => {
    vi.mocked(listProjects).mockResolvedValue([makeProject()])

    const queryClient = renderDashboard()

    await screen.findByRole('link', { name: 'My Todo App' })
    expect(queryClient.getQueryData(['projects'])).toEqual([makeProject()])
  })
})

describe('Dashboard 상태', () => {
  it('불러오는 동안 로딩 안내를 보여준다', () => {
    vi.mocked(listProjects).mockReturnValue(new Promise(() => undefined))

    renderDashboard()

    expect(screen.getByRole('status')).toHaveTextContent('프로젝트를 불러오는 중입니다...')
  })

  it('프로젝트가 없으면 빈 상태 안내를 보여준다', async () => {
    vi.mocked(listProjects).mockResolvedValue([])

    renderDashboard()

    expect(await screen.findByText('아직 프로젝트가 없습니다.')).toBeInTheDocument()
    expect(screen.queryByRole('status')).not.toBeInTheDocument()
  })

  it('실패하면 서버가 준 메시지를 알림으로 보여주고, 다시 시도하면 목록을 불러온다', async () => {
    vi.mocked(listProjects)
      .mockRejectedValueOnce(
        new ApiError({ code: 'network_error', message: '서버에 연결할 수 없습니다.' }),
      )
      .mockResolvedValueOnce([makeProject()])

    renderDashboard()

    expect(await screen.findByRole('alert')).toHaveTextContent('서버에 연결할 수 없습니다.')
    await userEvent.click(screen.getByRole('button', { name: '다시 시도' }))

    expect(await screen.findByRole('link', { name: 'My Todo App' })).toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('Error가 아닌 값으로 실패해도 기술 용어 없이 일반 안내를 보여준다', async () => {
    vi.mocked(listProjects).mockRejectedValue('boom')

    renderDashboard()

    expect(await screen.findByRole('alert')).toHaveTextContent(
      '프로젝트를 불러오지 못했습니다. 잠시 후 다시 시도하세요.',
    )
  })
})

describe('Dashboard 프로젝트 생성 플로우', () => {
  it('"새 프로젝트" 버튼을 누르면 생성 대화상자가 열린다', async () => {
    vi.mocked(listProjects).mockResolvedValue([makeProject()])
    renderDashboard()
    await screen.findByRole('link', { name: 'My Todo App' })

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: '새 프로젝트' }))

    expect(screen.getByRole('dialog', { name: '새 프로젝트 만들기' })).toBeInTheDocument()
  })

  it('빈 상태의 "첫 프로젝트 만들기" 버튼으로도 생성 대화상자를 연다', async () => {
    vi.mocked(listProjects).mockResolvedValue([])
    renderDashboard()

    await userEvent.click(await screen.findByRole('button', { name: '첫 프로젝트 만들기' }))

    expect(screen.getByRole('dialog', { name: '새 프로젝트 만들기' })).toBeInTheDocument()
  })

  it('프로젝트가 있으면 "첫 프로젝트 만들기" 버튼은 보이지 않는다', async () => {
    vi.mocked(listProjects).mockResolvedValue([makeProject()])
    renderDashboard()

    await screen.findByRole('link', { name: 'My Todo App' })

    expect(screen.queryByRole('button', { name: '첫 프로젝트 만들기' })).not.toBeInTheDocument()
  })

  it('만들기에 성공하면 대화상자를 닫고 목록을 다시 불러와 새 프로젝트를 보여준다', async () => {
    const created = makeProject({ id: 'p-2', title: '새로 만든 프로젝트' })
    vi.mocked(listProjects).mockResolvedValueOnce([]).mockResolvedValueOnce([created])
    vi.mocked(createProject).mockResolvedValue(created)
    renderDashboard()

    await userEvent.click(await screen.findByRole('button', { name: '첫 프로젝트 만들기' }))
    await userEvent.type(screen.getByLabelText('프로젝트 제목'), '새로 만든 프로젝트')
    await userEvent.click(screen.getByRole('button', { name: '만들기' }))

    expect(await screen.findByRole('link', { name: '새로 만든 프로젝트' })).toBeInTheDocument()
    expect(createProject).toHaveBeenCalledWith({ title: '새로 만든 프로젝트', description: null })
    expect(listProjects).toHaveBeenCalledTimes(2)
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
  })

  it('서버가 제목 오류를 주면 대화상자를 유지하고 제목 오류를 보여준다', async () => {
    vi.mocked(listProjects).mockResolvedValue([makeProject()])
    vi.mocked(createProject).mockRejectedValue(
      new ApiError({
        code: 'validation_error',
        message: '제목은 1자 이상 255자 이하여야 합니다.',
        status: 400,
        details: { field: 'title' },
      }),
    )
    renderDashboard()
    await screen.findByRole('link', { name: 'My Todo App' })

    await userEvent.click(screen.getByRole('button', { name: '새 프로젝트' }))
    await userEvent.type(screen.getByLabelText('프로젝트 제목'), '제목')
    await userEvent.click(screen.getByRole('button', { name: '만들기' }))

    expect(await screen.findByText('제목은 1자 이상 255자 이하여야 합니다.')).toBeInTheDocument()
    expect(screen.getByRole('dialog')).toBeInTheDocument()
  })

  it('취소하면 대화상자가 닫히고 포커스가 "새 프로젝트" 버튼으로 돌아간다', async () => {
    vi.mocked(listProjects).mockResolvedValue([makeProject()])
    renderDashboard()
    await screen.findByRole('link', { name: 'My Todo App' })

    await userEvent.click(screen.getByRole('button', { name: '새 프로젝트' }))
    await userEvent.click(screen.getByRole('button', { name: '취소' }))

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    await waitFor(() => expect(screen.getByRole('button', { name: '새 프로젝트' })).toHaveFocus())
    expect(createProject).not.toHaveBeenCalled()
  })
})
