import { QueryClient } from '@tanstack/react-query'
import { queryClient, shouldRetry } from '../../src/lib/queryClient'

const httpError = (status: number) => ({ response: { status } })

describe('queryClient', () => {
  it('QueryClient 인스턴스를 내보낸다', () => {
    expect(queryClient).toBeInstanceOf(QueryClient)
  })

  it('쿼리 기본 옵션: 30초 동안 fresh, 창 포커스 시 자동 재조회 안 함', () => {
    const options = queryClient.getDefaultOptions().queries

    expect(options?.staleTime).toBe(30_000)
    expect(options?.refetchOnWindowFocus).toBe(false)
  })

  it('쿼리 재시도 정책으로 shouldRetry를 사용한다', () => {
    expect(queryClient.getDefaultOptions().queries?.retry).toBe(shouldRetry)
  })

  it('뮤테이션은 재시도하지 않는다', () => {
    expect(queryClient.getDefaultOptions().mutations?.retry).toBe(false)
  })
})

describe('shouldRetry', () => {
  it.each([400, 401, 403, 404, 422, 499])('HTTP %i 오류는 재시도하지 않는다', (status) => {
    expect(shouldRetry(0, httpError(status))).toBe(false)
  })

  it.each([500, 502, 503])('HTTP %i 오류는 재시도한다', (status) => {
    expect(shouldRetry(0, httpError(status))).toBe(true)
  })

  it('응답이 없는 네트워크 오류는 재시도한다', () => {
    expect(shouldRetry(0, new Error('Network Error'))).toBe(true)
  })

  it('오류 값이 null이어도 예외 없이 재시도 여부를 판단한다', () => {
    expect(shouldRetry(0, null)).toBe(true)
  })

  it('최대 2회까지만 재시도한다', () => {
    expect(shouldRetry(1, httpError(500))).toBe(true)
    expect(shouldRetry(2, httpError(500))).toBe(false)
  })
})
