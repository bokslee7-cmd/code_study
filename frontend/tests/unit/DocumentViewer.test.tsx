import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import DocumentViewer from '../../src/components/document/DocumentViewer'
import { ApiError, apiClient } from '../../src/services/api-client'
import { makeContent, makeFile, mockDocumentApi, serverDocument } from '../fixtures/document'

vi.mock('../../src/components/document/CodeEditor', () => ({
  default: (props: {
    value: string
    path?: string
    highlightLine?: number | null
    onTopLineChange?: (line: number) => void
  }) => (
    <div data-testid="editor" data-path={props.path} data-highlight={props.highlightLine ?? ''}>
      <pre>{props.value}</pre>
      <button onClick={() => props.onTopLineChange?.(2)}>코드 스크롤</button>
    </div>
  ),
}))

const scrollIntoView = vi.fn()

beforeEach(() => {
  scrollIntoView.mockClear()
  Element.prototype.scrollIntoView = scrollIntoView
})

afterEach(() => {
  vi.restoreAllMocks()
})

function renderViewer() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={queryClient}>
      <DocumentViewer taskId="t-1" />
    </QueryClientProvider>,
  )
}

const chapterButton = (name: RegExp) =>
  within(screen.getByRole('navigation', { name: '챕터 이동' })).getByRole('button', { name })

describe('DocumentViewer 2열 레이아웃', () => {
  it('문서를 task id로 조회해 코드 영역과 설명 영역을 나란히 보여준다', async () => {
    const get = mockDocumentApi(apiClient, { document: () => serverDocument() })

    renderViewer()

    const code = await screen.findByRole('region', { name: '코드' })
    const explanation = screen.getByRole('region', { name: '설명' })
    expect(get).toHaveBeenCalledWith('/tasks/t-1/document')
    expect(within(code).getByText('main.py')).toBeInTheDocument()
    expect(within(code).getByTestId('editor')).toHaveTextContent('def add(a, b):')
    expect(within(explanation).getByText('두 수를 더해 주는 코드입니다.')).toBeInTheDocument()
  })

  it('두 영역은 넓은 화면에서 2열 그리드로 배치된다', async () => {
    mockDocumentApi(apiClient, { document: () => serverDocument() })

    renderViewer()

    const code = await screen.findByRole('region', { name: '코드' })
    expect(code.parentElement).toHaveClass('lg:grid-cols-2')
  })

  it('여러 파일이면 모든 파일을 코드 영역의 탭으로 보여준다', async () => {
    mockDocumentApi(apiClient, {
      document: () =>
        serverDocument({
          files: [makeFile({ path: 'main.py' }), makeFile({ path: 'util.py' })],
        }),
    })

    renderViewer()

    expect(await screen.findByRole('tab', { name: 'util.py' })).toBeInTheDocument()
  })
})

describe('DocumentViewer 코드와 설명 동기화', () => {
  it('코드를 스크롤하면 4장에서 그 줄의 해설로 스크롤하고 현재 항목으로 표시한다', async () => {
    mockDocumentApi(apiClient, { document: () => serverDocument() })
    renderViewer()
    await screen.findByRole('region', { name: '코드' })
    await userEvent.click(chapterButton(/4\./))
    scrollIntoView.mockClear()

    await userEvent.click(screen.getByRole('button', { name: '코드 스크롤' }))

    const articles = screen.getAllByRole('article')
    expect(articles[1]).toHaveAttribute('aria-current', 'true')
    expect(scrollIntoView.mock.instances).toContain(articles[1])
  })

  it('4장의 줄 번호를 누르면 코드에서 그 줄을 강조한다', async () => {
    mockDocumentApi(apiClient, { document: () => serverDocument() })
    renderViewer()
    await screen.findByRole('region', { name: '코드' })
    await userEvent.click(chapterButton(/4\./))

    await userEvent.click(screen.getByRole('button', { name: '줄 2' }))

    expect(screen.getByTestId('editor')).toHaveAttribute('data-highlight', '2')
  })

  it('코드 스크롤로 정해진 줄은 코드 강조로 되돌려 보내지 않는다', async () => {
    mockDocumentApi(apiClient, { document: () => serverDocument() })
    renderViewer()
    await screen.findByRole('region', { name: '코드' })
    await userEvent.click(chapterButton(/4\./))

    await userEvent.click(screen.getByRole('button', { name: '코드 스크롤' }))

    expect(screen.getByTestId('editor')).toHaveAttribute('data-highlight', '')
  })

  it('4장이 아닌 챕터를 보는 중에 코드를 스크롤해도 문제없이 동작한다', async () => {
    mockDocumentApi(apiClient, { document: () => serverDocument() })
    renderViewer()
    await screen.findByRole('region', { name: '코드' })

    await userEvent.click(screen.getByRole('button', { name: '코드 스크롤' }))

    expect(screen.getByText('두 수를 더해 주는 코드입니다.')).toBeInTheDocument()
  })
})

describe('DocumentViewer 부분 성공·실패 안내', () => {
  it('일부 챕터가 실패한 문서는 노란 경고 배너와 함께 보여준다', async () => {
    mockDocumentApi(apiClient, {
      document: () =>
        serverDocument({
          failed_chapters: ['chapter4'],
          content: makeContent({ chapter4: { generation_failed: true } }),
        }),
    })

    renderViewer()

    await screen.findByRole('region', { name: '설명' })
    const banner = screen.getByRole('status')
    expect(banner).toHaveTextContent('일부 섹션을 만들지 못했습니다. 질문하기로 보충할 수 있어요.')
    expect(banner).toHaveClass('bg-yellow-50')
    expect(screen.getByRole('region', { name: '설명' })).toBeInTheDocument()
  })

  it('실패 챕터를 열면 생성 실패 안내로 바뀐다', async () => {
    mockDocumentApi(apiClient, {
      document: () =>
        serverDocument({
          failed_chapters: ['chapter4'],
          content: makeContent({ chapter4: { generation_failed: true } }),
        }),
    })
    renderViewer()
    await screen.findByRole('region', { name: '설명' })

    await userEvent.click(chapterButton(/4\./))

    expect(screen.getByText('생성 실패')).toBeInTheDocument()
  })

  it('실패 챕터가 없으면 경고 배너를 그리지 않는다', async () => {
    mockDocumentApi(apiClient, { document: () => serverDocument() })

    renderViewer()

    await screen.findByRole('region', { name: '설명' })
    expect(screen.queryByRole('status')).not.toBeInTheDocument()
  })

  it('문서 전체가 failed면 빨간 오류 배너를 보여주고 코드·설명 영역은 그리지 않는다', async () => {
    mockDocumentApi(apiClient, {
      document: () =>
        serverDocument({ status: 'failed', generation_error: 'AI 서비스가 응답하지 않았습니다' }),
    })

    renderViewer()

    const banner = await screen.findByRole('alert')
    expect(banner).toHaveTextContent('문서를 만들지 못했습니다.')
    expect(banner).toHaveTextContent('AI 서비스가 응답하지 않았습니다')
    expect(banner).toHaveClass('bg-red-50')
    expect(screen.queryByRole('region', { name: '코드' })).not.toBeInTheDocument()
  })
})

describe('DocumentViewer 조회 오류', () => {
  it('문서가 아직 없으면 안내 문구를 보여준다', async () => {
    mockDocumentApi(apiClient, {
      document: () => new ApiError({ code: 'not_found', message: '문서가 없습니다.', status: 404 }),
    })

    renderViewer()

    expect(await screen.findByText('아직 문서가 없습니다.')).toBeInTheDocument()
  })

  it('조회에 실패하면 오류 메시지와 다시 시도 버튼을 보여주고 누르면 다시 조회한다', async () => {
    let fail = true
    mockDocumentApi(apiClient, {
      document: () =>
        fail
          ? new ApiError({ code: 'server_error', message: '서버 오류가 났습니다.', status: 500 })
          : serverDocument(),
    })
    renderViewer()

    expect(await screen.findByRole('alert')).toHaveTextContent('서버 오류가 났습니다.')
    fail = false
    await userEvent.click(screen.getByRole('button', { name: '다시 시도' }))

    expect(await screen.findByRole('region', { name: '코드' })).toBeInTheDocument()
  })

  it('Error가 아닌 값으로 실패해도 일반 안내를 보여준다', async () => {
    vi.spyOn(apiClient, 'get').mockRejectedValue('boom')

    renderViewer()

    expect(await screen.findByRole('alert')).toHaveTextContent(
      '문서를 불러오지 못했습니다. 잠시 후 다시 시도하세요.',
    )
  })
})
