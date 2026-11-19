import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import ProjectDetail from '../../src/pages/ProjectDetail'
import { ApiError } from '../../src/services/api-client'
import { getProject } from '../../src/services/project-service'
import { createTask, listTasks } from '../../src/services/task-service'
import { makeProject } from '../fixtures/project'
import { makeTask } from '../fixtures/task'

vi.mock('../../src/services/project-service')
vi.mock('../../src/services/task-service')

function renderDetail() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/projects/p-1']}>
        <Routes>
          <Route path="/projects/:projectId" element={<ProjectDetail />} />
          <Route path="/projects/:projectId/tasks/:taskId" element={<p>태스크 상세 화면</p>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
  return queryClient
}

const backLink = () => screen.getByRole('link', { name: '대시보드로 돌아가기' })

beforeEach(() => {
  vi.mocked(listTasks).mockResolvedValue([])
})

afterEach(() => {
  vi.resetAllMocks()
})

describe('ProjectDetail 정보', () => {
  it('주소의 프로젝트 id로 조회해 제목·설명·생성일·진행률을 보여준다', async () => {
    vi.mocked(getProject).mockResolvedValue(
      makeProject({ taskCount: 5, completedTaskCount: 2, progressPercent: 40 }),
    )

    renderDetail()

    expect(
      await screen.findByRole('heading', { level: 1, name: 'My Todo App' }),
    ).toBeInTheDocument()
    expect(getProject).toHaveBeenCalledWith('p-1')
    expect(screen.getByText('할 일 앱을 만들며 배우는 프로젝트')).toBeInTheDocument()
    expect(screen.getByText('생성일: 2026년 11월 1일')).toBeInTheDocument()
    expect(screen.getByText('2/5 태스크 완료')).toBeInTheDocument()
    expect(screen.getByRole('progressbar', { name: '진행률' })).toHaveAttribute(
      'aria-valuenow',
      '40',
    )
  })

  it('쿼리 키는 ["projects", id]다', async () => {
    vi.mocked(getProject).mockResolvedValue(makeProject())

    const queryClient = renderDetail()

    await screen.findByRole('heading', { name: 'My Todo App' })
    expect(queryClient.getQueryData(['projects', 'p-1'])).toEqual(makeProject())
  })

  it('설명이 없으면 "설명이 없습니다."를 보여준다', async () => {
    vi.mocked(getProject).mockResolvedValue(makeProject({ description: null }))

    renderDetail()

    expect(await screen.findByText('설명이 없습니다.')).toBeInTheDocument()
  })

  it('"태스크 타임라인" 제목을 보여준다', async () => {
    vi.mocked(getProject).mockResolvedValue(makeProject())

    renderDetail()

    expect(
      await screen.findByRole('heading', { level: 2, name: '태스크 타임라인' }),
    ).toBeInTheDocument()
  })

  it('대시보드로 돌아가는 링크를 제공한다', async () => {
    vi.mocked(getProject).mockResolvedValue(makeProject())

    renderDetail()

    await screen.findByRole('heading', { name: 'My Todo App' })
    expect(backLink()).toHaveAttribute('href', '/dashboard')
  })
})

describe('ProjectDetail 상태', () => {
  it('불러오는 동안 로딩 안내와 돌아가기 링크를 보여준다', () => {
    vi.mocked(getProject).mockReturnValue(new Promise(() => undefined))

    renderDetail()

    expect(screen.getByRole('status')).toHaveTextContent('프로젝트를 불러오는 중입니다...')
    expect(backLink()).toBeInTheDocument()
  })

  it('403이면 권한 없음 안내를 보여주고 다시 시도 버튼은 없다', async () => {
    vi.mocked(getProject).mockRejectedValue(
      new ApiError({ code: 'forbidden', message: 'Forbidden', status: 403 }),
    )

    renderDetail()

    expect(await screen.findByRole('alert')).toHaveTextContent(
      '이 프로젝트에 접근할 권한이 없습니다.',
    )
    expect(screen.queryByRole('button', { name: '다시 시도' })).not.toBeInTheDocument()
    expect(backLink()).toBeInTheDocument()
  })

  it('404이면 찾을 수 없음 안내를 보여주고 다시 시도 버튼은 없다', async () => {
    vi.mocked(getProject).mockRejectedValue(
      new ApiError({ code: 'not_found', message: 'Not found', status: 404 }),
    )

    renderDetail()

    expect(await screen.findByRole('alert')).toHaveTextContent(
      '프로젝트를 찾을 수 없습니다. 삭제되었거나 주소가 잘못되었을 수 있습니다.',
    )
    expect(screen.queryByRole('button', { name: '다시 시도' })).not.toBeInTheDocument()
    expect(backLink()).toBeInTheDocument()
  })

  it('그 밖의 오류는 서버가 준 메시지를 보여주고 다시 시도하면 불러온다', async () => {
    vi.mocked(getProject)
      .mockRejectedValueOnce(
        new ApiError({ code: 'network_error', message: '서버에 연결할 수 없습니다.' }),
      )
      .mockResolvedValueOnce(makeProject())

    renderDetail()

    expect(await screen.findByRole('alert')).toHaveTextContent('서버에 연결할 수 없습니다.')
    await userEvent.click(screen.getByRole('button', { name: '다시 시도' }))

    expect(await screen.findByRole('heading', { name: 'My Todo App' })).toBeInTheDocument()
  })

  it('Error가 아닌 값으로 실패해도 일반 안내를 보여준다', async () => {
    vi.mocked(getProject).mockRejectedValue('boom')

    renderDetail()

    expect(await screen.findByRole('alert')).toHaveTextContent(
      '프로젝트를 불러오지 못했습니다. 잠시 후 다시 시도하세요.',
    )
  })
})

describe('ProjectDetail 태스크 타임라인', () => {
  it('프로젝트의 태스크를 번호 순서대로 카드로 보여준다', async () => {
    vi.mocked(getProject).mockResolvedValue(makeProject())
    vi.mocked(listTasks).mockResolvedValue([
      makeTask({ id: 't-1', taskNumber: 1, title: 'Add Todo Function' }),
      makeTask({ id: 't-2', taskNumber: 2, title: 'Display List Items' }),
    ])

    renderDetail()

    const links = await screen.findAllByRole('link', {
      name: /Add Todo Function|Display List Items/,
    })
    expect(links.map((link) => link.textContent)).toEqual([
      'Add Todo Function',
      'Display List Items',
    ])
    expect(listTasks).toHaveBeenCalledWith('p-1')
  })

  it('쿼리 키는 ["projects", id, "tasks"]다', async () => {
    vi.mocked(getProject).mockResolvedValue(makeProject())
    vi.mocked(listTasks).mockResolvedValue([makeTask()])

    const queryClient = renderDetail()

    await screen.findByRole('link', { name: 'Add Todo Function' })
    expect(queryClient.getQueryData(['projects', 'p-1', 'tasks'])).toEqual([makeTask()])
  })

  it('불러오는 동안 안내를 보여준다', async () => {
    vi.mocked(getProject).mockResolvedValue(makeProject())
    vi.mocked(listTasks).mockReturnValue(new Promise(() => undefined))

    renderDetail()

    expect(await screen.findByText('태스크를 불러오는 중입니다...')).toBeInTheDocument()
  })

  it('태스크가 없으면 빈 상태 안내를 보여준다', async () => {
    vi.mocked(getProject).mockResolvedValue(makeProject())

    renderDetail()

    expect(
      await screen.findByText('아직 태스크가 없습니다. 첫 태스크를 만들어 보세요.'),
    ).toBeInTheDocument()
  })

  it('태스크 목록 오류는 메시지와 다시 시도 버튼을 보여주고, 다시 시도하면 불러온다', async () => {
    vi.mocked(getProject).mockResolvedValue(makeProject())
    vi.mocked(listTasks)
      .mockRejectedValueOnce(
        new ApiError({ code: 'network_error', message: '서버에 연결할 수 없습니다.' }),
      )
      .mockResolvedValueOnce([makeTask()])

    renderDetail()

    expect(await screen.findByRole('alert')).toHaveTextContent('서버에 연결할 수 없습니다.')
    await userEvent.click(screen.getByRole('button', { name: '다시 시도' }))

    expect(await screen.findByRole('link', { name: 'Add Todo Function' })).toBeInTheDocument()
  })

  it('Error가 아닌 값으로 실패하면 일반 안내를 보여준다', async () => {
    vi.mocked(getProject).mockResolvedValue(makeProject())
    vi.mocked(listTasks).mockRejectedValue('boom')

    renderDetail()

    expect(await screen.findByRole('alert')).toHaveTextContent(
      '태스크를 불러오지 못했습니다. 잠시 후 다시 시도하세요.',
    )
  })
})

describe('ProjectDetail 태스크 만들기', () => {
  async function openModal() {
    await screen.findByRole('heading', { name: 'My Todo App' })
    await userEvent.click(screen.getByRole('button', { name: '새 태스크' }))
  }

  it('"새 태스크" 버튼으로 생성 모달을 연다', async () => {
    vi.mocked(getProject).mockResolvedValue(makeProject())

    renderDetail()
    await openModal()

    expect(screen.getByRole('dialog', { name: '새 태스크 만들기' })).toBeInTheDocument()
  })

  it('생성하면 createTask를 호출하고 목록을 갱신한 뒤 태스크 상세로 이동한다', async () => {
    vi.mocked(getProject).mockResolvedValue(makeProject())
    vi.mocked(createTask).mockResolvedValue(makeTask({ id: 't-9', taskNumber: 1 }))

    const queryClient = renderDetail()
    const invalidate = vi.spyOn(queryClient, 'invalidateQueries')
    await openModal()
    await userEvent.type(screen.getByLabelText('태스크 제목'), 'Add Todo Function')
    await userEvent.click(screen.getByRole('tab', { name: '코드 붙여넣기' }))
    await userEvent.selectOptions(screen.getByLabelText('프로그래밍 언어'), 'python')
    await userEvent.click(screen.getByLabelText('코드'))
    await userEvent.paste('print(1)')
    await userEvent.click(screen.getByRole('button', { name: '태스크 만들기' }))

    expect(await screen.findByText('태스크 상세 화면')).toBeInTheDocument()
    expect(createTask).toHaveBeenCalledWith('p-1', {
      title: 'Add Todo Function',
      description: null,
      uploadMethod: 'paste',
      code: 'print(1)',
      language: 'python',
    })
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ['projects'] })
  })

  it('생성에 실패하면 모달에 오류를 보여주고 이동하지 않는다', async () => {
    vi.mocked(getProject).mockResolvedValue(makeProject())
    vi.mocked(createTask).mockRejectedValue(
      new ApiError({
        code: 'too_many_files',
        message: '업로드당 최대 20개 파일까지 가능합니다.',
        status: 400,
      }),
    )

    renderDetail()
    await openModal()
    await userEvent.type(screen.getByLabelText('태스크 제목'), 'Add Todo Function')
    await userEvent.click(screen.getByRole('tab', { name: '코드 붙여넣기' }))
    await userEvent.selectOptions(screen.getByLabelText('프로그래밍 언어'), 'python')
    await userEvent.click(screen.getByLabelText('코드'))
    await userEvent.paste('print(1)')
    await userEvent.click(screen.getByRole('button', { name: '태스크 만들기' }))

    expect(await screen.findByText('업로드당 최대 20개 파일까지 가능합니다.')).toBeInTheDocument()
    expect(screen.queryByText('태스크 상세 화면')).not.toBeInTheDocument()
  })
})
