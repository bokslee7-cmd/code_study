const SECONDS_PER_MINUTE = 60

// 문서 생성 예상 남은 시간을 사람이 읽는 말로 바꾼다. 값이 없으면 계산 중이라고 알린다.
export function formatRemainingTime(seconds: number | null): string {
  if (seconds === null) return '예상 시간을 계산하는 중입니다'
  if (seconds <= 0) return '곧 완료됩니다'
  const minutes = Math.floor(seconds / SECONDS_PER_MINUTE)
  const rest = seconds % SECONDS_PER_MINUTE
  if (minutes === 0) return `약 ${rest}초`
  return rest === 0 ? `약 ${minutes}분` : `약 ${minutes}분 ${rest}초`
}
