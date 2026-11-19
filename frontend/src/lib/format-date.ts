// ISO8601 문자열을 "2026년 11월 5일" 형태의 한국어 날짜로 바꾼다.
export function formatDate(isoString: string): string {
  return new Date(isoString).toLocaleDateString('ko-KR', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  })
}
