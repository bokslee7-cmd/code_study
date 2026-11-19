import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { AxiosResponse } from 'axios'
import type { ReactElement } from 'react'
import { MemoryRouter } from 'react-router-dom'
import App from '../../src/App'
import DevTestPage from '../../src/pages/DevTestPage'
import { ApiError, apiClient } from '../../src/services/api-client'

const healthResponse = { data: { status: 'ok' } } as AxiosResponse

function renderWithQuery(ui: ReactElement) {
  return render(<QueryClientProvider client={new QueryClient()}>{ui}</QueryClientProvider>)
}

afterEach(() => {
  vi.restoreAllMocks()
})

describe('DevTestPage', () => {
  it('제목, "API 호출" 버튼, 응답 표시 영역을 보여주고 아직 호출하지 않는다', () => {
    const get = vi.spyOn(apiClient, 'get')

    renderWithQuery(<DevTestPage />)

    expect(screen.getByRole('heading', { name: '개발용 API 테스트' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'API 호출' })).toBeEnabled()
    expect(screen.getByRole('region', { name: '응답' })).toHaveTextContent(
      '아직 호출하지 않았습니다',
    )
    expect(get).not.toHaveBeenCalled()
  })

  it('버튼을 누르면 apiClient.get("/health")를 호출하고 응답을 JSON으로 보여준다', async () => {
    const get = vi.spyOn(apiClient, 'get').mockResolvedValue(healthResponse)
    renderWithQuery(<DevTestPage />)

    await userEvent.click(screen.getByRole('button', { name: 'API 호출' }))

    await waitFor(() =>
      expect(screen.getByRole('region', { name: '응답' })).toHaveTextContent('"status": "ok"'),
    )
    expect(get).toHaveBeenCalledTimes(1)
    expect(get.mock.calls[0][0]).toBe('/health')
  })

  it('요청 중에는 "로딩 중..."을 보여주고 버튼을 비활성화한다', async () => {
    let resolveRequest: (value: AxiosResponse) => void = () => {}
    vi.spyOn(apiClient, 'get').mockReturnValue(
      new Promise<AxiosResponse>((resolve) => {
        resolveRequest = resolve
      }),
    )
    renderWithQuery(<DevTestPage />)

    await userEvent.click(screen.getByRole('button', { name: 'API 호출' }))

    expect(await screen.findByText('로딩 중...')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'API 호출' })).toBeDisabled()

    resolveRequest(healthResponse)

    await waitFor(() => expect(screen.queryByText('로딩 중...')).not.toBeInTheDocument())
    expect(screen.getByRole('button', { name: 'API 호출' })).toBeEnabled()
  })

  it('요청이 실패하면 ApiError의 코드와 메시지를 보여준다', async () => {
    vi.spyOn(apiClient, 'get').mockRejectedValue(
      new ApiError({ code: 'network_error', message: '서버에 연결할 수 없습니다.' }),
    )
    renderWithQuery(<DevTestPage />)

    await userEvent.click(screen.getByRole('button', { name: 'API 호출' }))

    const region = await screen.findByRole('region', { name: '응답' })
    await waitFor(() => expect(region).toHaveTextContent('network_error'))
    expect(region).toHaveTextContent('서버에 연결할 수 없습니다.')
  })

  it('다시 누르면 API를 다시 호출한다', async () => {
    const get = vi.spyOn(apiClient, 'get').mockResolvedValue(healthResponse)
    renderWithQuery(<DevTestPage />)

    await userEvent.click(screen.getByRole('button', { name: 'API 호출' }))
    await waitFor(() => expect(get).toHaveBeenCalledTimes(1))
    await waitFor(() => expect(screen.getByRole('button', { name: 'API 호출' })).toBeEnabled())
    await userEvent.click(screen.getByRole('button', { name: 'API 호출' }))

    await waitFor(() => expect(get).toHaveBeenCalledTimes(2))
  })
})

describe('/dev-test 라우트', () => {
  it('App의 /dev-test 경로에서 테스트 페이지를 렌더링한다', () => {
    renderWithQuery(
      <MemoryRouter initialEntries={['/dev-test']}>
        <App />
      </MemoryRouter>,
    )

    expect(screen.getByRole('heading', { name: '개발용 API 테스트' })).toBeInTheDocument()
  })
})
