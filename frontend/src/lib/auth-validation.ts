// backend/src/utils/security.py 의 MIN_PASSWORD_LENGTH 와 같은 값이어야 한다.
export const MIN_PASSWORD_LENGTH = 8

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

export function validateEmail(email: string): string | null {
  if (email.trim() === '') return '이메일을 입력하세요.'
  if (!EMAIL_PATTERN.test(email.trim())) return '올바른 이메일 형식이 아닙니다.'
  return null
}

// 로그인: 가입 당시 규칙이 지금과 달라도 기존 사용자를 막지 않도록 입력 여부만 확인한다.
export function validateRequiredPassword(password: string): string | null {
  return password === '' ? '비밀번호를 입력하세요.' : null
}

export function validateNewPassword(password: string): string | null {
  if (password === '') return '비밀번호를 입력하세요.'
  if (password.length < MIN_PASSWORD_LENGTH) {
    return `비밀번호는 ${MIN_PASSWORD_LENGTH}자 이상이어야 합니다.`
  }
  return null
}
