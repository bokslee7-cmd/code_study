import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import TaskDetail from '../../src/pages/TaskDetail'
import { ApiError, apiClient } from '../../src/services/api-client'
import { getTask } from '../../src/services/task-service'
import { mockDocumentApi, serverDocument } from '../fixtures/document'
import { makeTask } from '../fixtures/task'

vi.mock('../../src/services/task-service')
vi.mock('../../src/components/document/CodeEditor', () => ({
  default: ({ value }: { value: string }) => <pre data-testid="editor">{value}</pre>,
}))

const documentNotFound = () =>
  new ApiError({ code: 'not_found', message: '문서가 없습니다.', status: 404 })

beforeEach(() => {
  Element.prototype.scrollIntoView = vi.fn()
  mockDocumentApi(apiClient, { document: documentNotFound })
})

function renderDetail() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/projects/p-1/tasks/t-1']}>
        <Routes>
          <Route path="/projects/:projectId/tasks/:taskId" element={<TaskDetail />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
  return queryClient
}

const backLink = () => screen.getByRole('link', { name: '프로젝트로 돌아가기' })

afterEach(() => {
  vi.resetAllMocks()
})

describe('TaskDetail 정보', () => {
  it('주소의 태스크 id로 조회해 번호·제목·설명·생성일을 보여준다', async () => {
    vi.mocked(getTask).mockResolvedValue(makeTask())

    renderDetail()

    expect(
      await screen.findByRole('heading', { level: 1, name: 'Add Todo Function' }),
    ).toBeInTheDocument()
    expect(getTask).toHaveBeenCalledWith('t-1')
    expect(screen.getByText('Task 1')).toBeInTheDocument()
    expect(screen.getByText('할 일 추가 기능을 배운다')).toBeInTheDocument()
    expect(screen.getByText('생성일: 2026년 11월 2일')).toBeInTheDocument()
  })

  it('쿼리 키는 ["projects", projectId, "tasks", taskId]다', async () => {
    vi.mocked(getTask).mockResolvedValue(makeTask())

    const queryClient = renderDetail()

    await screen.findByRole('heading', { name: 'Add Todo Function' })
    expect(queryClient.getQueryData(['projects', 'p-1', 'tasks', 't-1'])).toEqual(makeTask())
  })

  it('설명이 없으면 설명 줄을 그리지 않는다', async () => {
    vi.mocked(getTask).mockResolvedValue(makeTask({ description: null }))

    renderDetail()

    await screen.findByRole('heading', { name: 'Add Todo Function' })
    expect(screen.queryByText('할 일 추가 기능을 배운다')).not.toBeInTheDocument()
  })

  it('프로젝트로 돌아가는 링크를 제공한다', async () => {
    vi.mocked(getTask).mockResolvedValue(makeTask())

    renderDetail()

    await screen.findByRole('heading', { name: 'Add Todo Function' })
    expect(backLink()).toHaveAttribute('href', '/projects/p-1')
  })
})

describe('TaskDetail 탭 골격', () => {
  it('문서·연습문제·Q&A 탭을 보여주고 기본은 문서 탭이다', async () => {
    vi.mocked(getTask).mockResolvedValue(makeTask())

    renderDetail()

    await screen.findByRole('heading', { name: 'Add Todo Function' })
    expect(screen.getAllByRole('tab').map((tab) => tab.textContent)).toEqual([
      '문서',
      '연습문제',
      'Q&A',
    ])
    expect(screen.getByRole('tab', { name: '문서' })).toHaveAttribute('aria-selected', 'true')
    expect(await screen.findByText('아직 문서가 없습니다.')).toBeInTheDocument()
  })

  it('문서 탭은 주소의 태스크 id로 문서를 조회해 코드와 설명을 보여준다', async () => {
    vi.mocked(getTask).mockResolvedValue(makeTask())
    const get = mockDocumentApi(apiClient, { document: () => serverDocument() })

    renderDetail()

    const panel = await screen.findByRole('tabpanel')
    expect(await within(panel).findByRole('region', { name: '코드' })).toBeInTheDocument()
    expect(get).toHaveBeenCalledWith('/tasks/t-1/document')
    expect(within(panel).getByText('두 수를 더해 주는 코드입니다.')).toBeInTheDocument()
  })

  it('문서 생성 중이면 문서 탭에 진행 상태를 보여준다', async () => {
    vi.mocked(getTask).mockResolvedValue(makeTask())
    mockDocumentApi(apiClient, {
      document: () => serverDocument({ status: 'in_progress', content: {} }),
      status: () => ({
        task_id: 't-1',
        status: 'in_progress',
        generation_started_at: null,
        generation_completed_at: null,
        generation_error: null,
        failed_chapters: [],
        estimated_remaining_seconds: 30,
      }),
    })

    renderDetail()

    expect(await screen.findByText('문서를 만드는 중입니다')).toBeInTheDocument()
    expect(await screen.findByText('예상 남은 시간: 약 30초')).toBeInTheDocument()
  })

  it('탭을 누르면 해당 준비 중 안내로 바뀐다', async () => {
    vi.mocked(getTask).mockResolvedValue(makeTask())

    renderDetail()
    await screen.findByRole('heading', { name: 'Add Todo Function' })

    await userEvent.click(screen.getByRole('tab', { name: '연습문제' }))
    expect(screen.getByRole('tabpanel')).toHaveTextContent('연습문제는 준비 중입니다.')

    await userEvent.click(screen.getByRole('tab', { name: 'Q&A' }))
    expect(screen.getByRole('tabpanel')).toHaveTextContent('Q&A는 준비 중입니다.')
  })
})

describe('TaskDetail 상태', () => {
  it('불러오는 동안 로딩 안내와 돌아가기 링크를 보여준다', () => {
    vi.mocked(getTask).mockReturnValue(new Promise(() => undefined))

    renderDetail()

    expect(screen.getByRole('status')).toHaveTextContent('태스크를 불러오는 중입니다...')
    expect(backLink()).toBeInTheDocument()
  })

  it('403이면 권한 없음 안내를 보여주고 다시 시도 버튼은 없다', async () => {
    vi.mocked(getTask).mockRejectedValue(
      new ApiError({ code: 'forbidden', message: 'Forbidden', status: 403 }),
    )

    renderDetail()

    expect(await screen.findByRole('alert')).toHaveTextContent(
      '이 태스크에 접근할 권한이 없습니다.',
    )
    expect(screen.queryByRole('button', { name: '다시 시도' })).not.toBeInTheDocument()
    expect(backLink()).toBeInTheDocument()
  })

  it('404이면 찾을 수 없음 안내를 보여주고 다시 시도 버튼은 없다', async () => {
    vi.mocked(getTask).mockRejectedValue(
      new ApiError({ code: 'not_found', message: 'Not found', status: 404 }),
    )

    renderDetail()

    expect(await screen.findByRole('alert')).toHaveTextContent(
      '태스크를 찾을 수 없습니다. 삭제되었거나 주소가 잘못되었을 수 있습니다.',
    )
    expect(screen.queryByRole('button', { name: '다시 시도' })).not.toBeInTheDocument()
  })

  it('그 밖의 오류는 서버 메시지를 보여주고 다시 시도하면 불러온다', async () => {
    vi.mocked(getTask)
      .mockRejectedValueOnce(
        new ApiError({ code: 'network_error', message: '서버에 연결할 수 없습니다.' }),
      )
      .mockResolvedValueOnce(makeTask())

    renderDetail()

    expect(await screen.findByRole('alert')).toHaveTextContent('서버에 연결할 수 없습니다.')
    await userEvent.click(screen.getByRole('button', { name: '다시 시도' }))

    expect(await screen.findByRole('heading', { name: 'Add Todo Function' })).toBeInTheDocument()
  })

  it('Error가 아닌 값으로 실패해도 일반 안내를 보여준다', async () => {
    vi.mocked(getTask).mockRejectedValue('boom')

    renderDetail()

    expect(await screen.findByRole('alert')).toHaveTextContent(
      '태스크를 불러오지 못했습니다. 잠시 후 다시 시도하세요.',
    )
  })
})
