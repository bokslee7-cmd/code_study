import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import DocumentViewer from '../../src/components/document/DocumentViewer'
import { formatRemainingTime } from '../../src/lib/format-remaining-time'
import { apiClient } from '../../src/services/api-client'
import { mockDocumentApi, serverDocument, serverStatus } from '../fixtures/document'

vi.mock('../../src/components/document/CodeEditor', () => ({
  default: () => <div data-testid="editor" />,
}))

beforeEach(() => {
  Element.prototype.scrollIntoView = vi.fn()
})

afterEach(() => {
  vi.restoreAllMocks()
  vi.useRealTimers()
})

function renderViewer() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={queryClient}>
      <DocumentViewer taskId="t-1" />
    </QueryClientProvider>,
  )
}

describe('formatRemainingTime', () => {
  it.each([
    [0, '곧 완료됩니다'],
    [1, '약 1초'],
    [40, '약 40초'],
    [60, '약 1분'],
    [90, '약 1분 30초'],
    [125, '약 2분 5초'],
  ])('%i초는 "%s"로 표시한다', (seconds, expected) => {
    expect(formatRemainingTime(seconds)).toBe(expected)
  })

  it('값이 없으면 계산 중 문구를 쓴다', () => {
    expect(formatRemainingTime(null)).toBe('예상 시간을 계산하는 중입니다')
  })
})

describe('DocumentViewer 로딩 상태', () => {
  it('문서를 조회하는 동안 불러오는 중 안내를 보여준다', () => {
    vi.spyOn(apiClient, 'get').mockReturnValue(new Promise(() => undefined))

    renderViewer()

    expect(screen.getByRole('status')).toHaveTextContent('문서를 불러오는 중입니다...')
  })

  it('in_progress면 진행 표시와 예상 남은 시간을 보여준다', async () => {
    mockDocumentApi(apiClient, {
      document: () => serverDocument({ status: 'in_progress', content: {} }),
      status: () => serverStatus({ estimated_remaining_seconds: 40 }),
    })

    renderViewer()

    expect(await screen.findByText('문서를 만드는 중입니다')).toBeInTheDocument()
    expect(screen.getByRole('progressbar', { name: '문서 생성 진행 상황' })).toBeInTheDocument()
    expect(await screen.findByText('예상 남은 시간: 약 40초')).toBeInTheDocument()
    expect(screen.queryByRole('region', { name: '코드' })).not.toBeInTheDocument()
  })

  it('pending이면 대기 중 문구를 보여준다', async () => {
    mockDocumentApi(apiClient, {
      document: () => serverDocument({ status: 'pending', content: {} }),
      status: () => serverStatus({ status: 'pending', estimated_remaining_seconds: null }),
    })

    renderViewer()

    expect(await screen.findByText('문서 생성을 기다리는 중입니다')).toBeInTheDocument()
    expect(await screen.findByText('예상 시간을 계산하는 중입니다')).toBeInTheDocument()
  })

  it('폴링으로 completed가 되면 문서를 보여준다', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    let finished = false
    mockDocumentApi(apiClient, {
      document: () =>
        finished ? serverDocument() : serverDocument({ status: 'in_progress', content: {} }),
      status: () => serverStatus({ status: finished ? 'completed' : 'in_progress' }),
    })
    renderViewer()
    await screen.findByText('문서를 만드는 중입니다')

    finished = true
    await vi.advanceTimersByTimeAsync(3000)

    expect(await screen.findByRole('region', { name: '코드' })).toBeInTheDocument()
    expect(screen.queryByRole('progressbar')).not.toBeInTheDocument()
  })

  it('failed면 사유와 재시도 안내를 보여준다', async () => {
    mockDocumentApi(apiClient, {
      document: () =>
        serverDocument({ status: 'failed', content: {}, generation_error: '서버가 바빴습니다' }),
    })

    renderViewer()

    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent('문서를 만들지 못했습니다.')
    expect(alert).toHaveTextContent('사유: 서버가 바빴습니다')
    expect(alert).toHaveTextContent('잠시 후 다시 시도해 주세요.')
  })

  it('failed인데 사유가 없으면 알 수 없는 오류로 표시한다', async () => {
    mockDocumentApi(apiClient, {
      document: () => serverDocument({ status: 'failed', content: {}, generation_error: null }),
    })

    renderViewer()

    expect(await screen.findByRole('alert')).toHaveTextContent('사유: 알 수 없는 오류')
  })

  it('failed 안내의 다시 확인 버튼은 문서를 다시 조회한다', async () => {
    const get = mockDocumentApi(apiClient, {
      document: () => serverDocument({ status: 'failed', content: {} }),
    })
    renderViewer()
    await screen.findByRole('alert')

    await userEvent.click(screen.getByRole('button', { name: '다시 확인' }))

    expect(get.mock.calls.filter(([url]) => url === '/tasks/t-1/document')).toHaveLength(2)
  })
})
