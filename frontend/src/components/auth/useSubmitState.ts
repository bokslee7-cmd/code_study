import { useState } from 'react'

const FALLBACK_ERROR_MESSAGE = '요청을 처리하지 못했습니다. 잠시 후 다시 시도하세요.'

// 폼 제출의 "진행 중 / 서버 오류" 상태를 관리한다. 서버 오류 메시지는 ApiError.message(한국어)를 그대로 쓴다.
export function useSubmitState<T>(onSubmit: (values: T) => Promise<void>) {
  const [isPending, setIsPending] = useState(false)
  const [serverError, setServerError] = useState<string | null>(null)

  async function submit(values: T): Promise<void> {
    setIsPending(true)
    setServerError(null)
    try {
      await onSubmit(values)
    } catch (error) {
      setServerError(error instanceof Error ? error.message : FALLBACK_ERROR_MESSAGE)
    } finally {
      setIsPending(false)
    }
  }

  return { isPending, serverError, submit }
}
