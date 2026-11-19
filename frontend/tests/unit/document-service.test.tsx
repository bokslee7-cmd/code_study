import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, renderHook, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { ApiError, apiClient } from '../../src/services/api-client'
import {
  POLL_INTERVAL_MS,
  getDocument,
  getDocumentStatus,
  useDocument,
} from '../../src/services/document-service'
import { makeDocument, makeStatus, serverDocument, serverStatus } from '../fixtures/document'

afterEach(() => {
  vi.restoreAllMocks()
  vi.useRealTimers()
})

const notFound = () =>
  new ApiError({ code: 'not_found', message: '아직 문서가 없습니다.', status: 404 })

describe('getDocument', () => {
  it('GET /tasks/{id}/document를 호출하고 camelCase 문서로 변환한다', async () => {
    const get = vi.spyOn(apiClient, 'get').mockResolvedValue({ data: serverDocument() })

    const document = await getDocument('t-1')

    expect(get).toHaveBeenCalledWith('/tasks/t-1/document')
    expect(document).toEqual(makeDocument())
  })

  it('content 안쪽 키는 변환하지 않고 그대로 둔다', async () => {
    vi.spyOn(apiClient, 'get').mockResolvedValue({
      data: serverDocument({
        content: { chapter3: { title: 't', flowchart: 'f', file_breakdown: { 'a_b.py': '역할' } } },
      }),
    })

    const document = await getDocument('t-1')

    expect(document?.content.chapter3).toEqual({
      title: 't',
      flowchart: 'f',
      file_breakdown: { 'a_b.py': '역할' },
    })
  })

  it('실패 챕터 목록과 생성 오류를 옮긴다', async () => {
    vi.spyOn(apiClient, 'get').mockResolvedValue({
      data: serverDocument({
        status: 'failed',
        failed_chapters: ['chapter4'],
        generation_error: 'AI 응답 오류',
      }),
    })

    const document = await getDocument('t-1')

    expect(document?.failedChapters).toEqual(['chapter4'])
    expect(document?.generationError).toBe('AI 응답 오류')
    expect(document?.status).toBe('failed')
  })

  it('404이면 null을 돌려준다(아직 문서가 없음)', async () => {
    vi.spyOn(apiClient, 'get').mockRejectedValue(notFound())

    await expect(getDocument('t-1')).resolves.toBeNull()
  })

  it('404가 아닌 오류는 그대로 던진다', async () => {
    const error = new ApiError({ code: 'server_error', message: '서버 오류', status: 500 })
    vi.spyOn(apiClient, 'get').mockRejectedValue(error)

    await expect(getDocument('t-1')).rejects.toBe(error)
  })
})

describe('getDocumentStatus', () => {
  it('GET /tasks/{id}/document/status를 호출하고 camelCase로 변환한다', async () => {
    const get = vi.spyOn(apiClient, 'get').mockResolvedValue({ data: serverStatus() })

    const status = await getDocumentStatus('t-1')

    expect(get).toHaveBeenCalledWith('/tasks/t-1/document/status')
    expect(status).toEqual(makeStatus())
  })
})

describe('useDocument', () => {
  function wrapper({ children }: { children: ReactNode }) {
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  }

  function mockApi(handlers: { document: () => unknown; status?: () => unknown }) {
    return vi.spyOn(apiClient, 'get').mockImplementation((url: string) => {
      if (url.endsWith('/document/status')) return Promise.resolve({ data: handlers.status?.() })
      const body = handlers.document()
      return body instanceof Error ? Promise.reject(body) : Promise.resolve({ data: body })
    })
  }

  const calls = (get: ReturnType<typeof mockApi>, suffix: string) =>
    get.mock.calls.filter(([url]) => (url as string).endsWith(suffix)).length

  it('완료된 문서는 한 번만 조회하고 상태 폴링은 하지 않는다', async () => {
    const get = mockApi({ document: () => serverDocument() })

    const { result } = renderHook(() => useDocument('t-1'), { wrapper })

    await waitFor(() => expect(result.current.document).toEqual(makeDocument()))
    expect(result.current.status).toBe('completed')
    expect(calls(get, '/document/status')).toBe(0)
  })

  it('문서가 없으면(404) document는 null이고 폴링하지 않는다', async () => {
    const get = mockApi({ document: () => notFound() })

    const { result } = renderHook(() => useDocument('t-1'), { wrapper })

    await waitFor(() => expect(result.current.isPending).toBe(false))
    expect(result.current.document).toBeNull()
    expect(result.current.status).toBeNull()
    expect(calls(get, '/document/status')).toBe(0)
  })

  it('진행 중이면 3초 간격으로 상태를 폴링하고 남은 시간을 알려준다', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    const get = mockApi({
      document: () => serverDocument({ status: 'in_progress' }),
      status: () => serverStatus({ estimated_remaining_seconds: 40 }),
    })

    const { result } = renderHook(() => useDocument('t-1'), { wrapper })

    await waitFor(() => expect(calls(get, '/document/status')).toBe(1))
    expect(result.current.status).toBe('in_progress')
    expect(result.current.estimatedRemainingSeconds).toBe(40)

    await act(() => vi.advanceTimersByTimeAsync(POLL_INTERVAL_MS))
    expect(calls(get, '/document/status')).toBe(2)
    await act(() => vi.advanceTimersByTimeAsync(POLL_INTERVAL_MS))
    expect(calls(get, '/document/status')).toBe(3)
  })

  it('폴링 간격은 3초다', () => {
    expect(POLL_INTERVAL_MS).toBe(3000)
  })

  it('상태가 completed가 되면 폴링을 멈추고 문서를 다시 조회한다', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    let finished = false
    const get = mockApi({
      document: () => serverDocument({ status: finished ? 'completed' : 'in_progress' }),
      status: () =>
        serverStatus({
          status: finished ? 'completed' : 'in_progress',
          estimated_remaining_seconds: finished ? null : 10,
        }),
    })

    const { result } = renderHook(() => useDocument('t-1'), { wrapper })
    await waitFor(() => expect(result.current.status).toBe('in_progress'))

    finished = true
    await act(() => vi.advanceTimersByTimeAsync(POLL_INTERVAL_MS))

    await waitFor(() => expect(result.current.document?.status).toBe('completed'))
    expect(result.current.status).toBe('completed')
    expect(calls(get, '/document')).toBe(2)

    const statusCalls = calls(get, '/document/status')
    await act(() => vi.advanceTimersByTimeAsync(POLL_INTERVAL_MS * 3))
    expect(calls(get, '/document/status')).toBe(statusCalls)
  })

  it('상태가 failed가 되어도 폴링을 멈추고 문서를 다시 조회한다', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    let failed = false
    const get = mockApi({
      document: () =>
        serverDocument({
          status: failed ? 'failed' : 'pending',
          generation_error: failed ? '실패' : null,
        }),
      status: () => serverStatus({ status: failed ? 'failed' : 'pending' }),
    })

    const { result } = renderHook(() => useDocument('t-1'), { wrapper })
    await waitFor(() => expect(result.current.status).toBe('pending'))

    failed = true
    await act(() => vi.advanceTimersByTimeAsync(POLL_INTERVAL_MS))

    await waitFor(() => expect(result.current.document?.generationError).toBe('실패'))
    const statusCalls = calls(get, '/document/status')
    await act(() => vi.advanceTimersByTimeAsync(POLL_INTERVAL_MS * 3))
    expect(calls(get, '/document/status')).toBe(statusCalls)
  })

  it('문서 조회가 실패하면 isError와 refetch를 제공한다', async () => {
    const error = new ApiError({ code: 'server_error', message: '서버 오류', status: 500 })
    mockApi({ document: () => error })

    const { result } = renderHook(() => useDocument('t-1'), { wrapper })

    await waitFor(() => expect(result.current.isError).toBe(true))
    expect(result.current.error).toBe(error)
    expect(typeof result.current.refetch).toBe('function')
  })
})
