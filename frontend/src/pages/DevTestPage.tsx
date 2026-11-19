import { useQuery } from '@tanstack/react-query'
import AuthStoreTest from '../components/dev/AuthStoreTest'
import TailwindTest from '../components/dev/TailwindTest'
import { apiClient, toApiError } from '../services/api-client'

// 개발 중 백엔드 연결을 확인하는 임시 페이지. 배포 전에 제거하거나 개발 모드에서만 노출한다.
export default function DevTestPage() {
  const { data, error, isFetching, isError, refetch } = useQuery({
    queryKey: ['dev-test', 'health'],
    queryFn: async () => (await apiClient.get<unknown>('/health')).data,
    enabled: false,
    retry: false,
  })

  const apiError = isError ? toApiError(error) : null

  return (
    <main>
      <h1>개발용 API 테스트</h1>
      <button type="button" onClick={() => refetch()} disabled={isFetching}>
        API 호출
      </button>
      <section aria-label="응답">
        {isFetching && <p>로딩 중...</p>}
        {!isFetching && apiError && (
          <p role="alert">
            {apiError.code}: {apiError.message}
          </p>
        )}
        {!isFetching && !apiError && data !== undefined && (
          <pre>{JSON.stringify(data, null, 2)}</pre>
        )}
        {!isFetching && !apiError && data === undefined && <p>아직 호출하지 않았습니다.</p>}
      </section>
      <AuthStoreTest />
      <TailwindTest />
    </main>
  )
}
