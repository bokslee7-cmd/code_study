// backend 프로젝트 제목 검증(공백 제거 후 1~255자)과 같은 규칙이어야 한다.
export const MAX_PROJECT_TITLE_LENGTH = 255

export function validateProjectTitle(title: string): string | null {
  const trimmed = title.trim()
  if (trimmed === '') return '프로젝트 제목을 입력하세요.'
  if (trimmed.length > MAX_PROJECT_TITLE_LENGTH) {
    return `프로젝트 제목은 ${MAX_PROJECT_TITLE_LENGTH}자 이하로 입력하세요.`
  }
  return null
}
