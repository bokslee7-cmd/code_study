import {
  MIN_PASSWORD_LENGTH,
  validateEmail,
  validateNewPassword,
  validateRequiredPassword,
} from '../../src/lib/auth-validation'

describe('validateEmail', () => {
  it.each(['a@b.co', 'learner+tag@example.com'])('"%s"는 통과한다', (email) => {
    expect(validateEmail(email)).toBeNull()
  })

  it('비어 있으면 입력 안내를 돌려준다', () => {
    expect(validateEmail('')).toBe('이메일을 입력하세요.')
    expect(validateEmail('   ')).toBe('이메일을 입력하세요.')
  })

  it.each(['plain', 'a@b', '@b.com', 'a b@c.com'])('"%s"는 형식 오류다', (email) => {
    expect(validateEmail(email)).toBe('올바른 이메일 형식이 아닙니다.')
  })
})

describe('validateRequiredPassword', () => {
  it('비어 있으면 입력 안내를 돌려준다', () => {
    expect(validateRequiredPassword('')).toBe('비밀번호를 입력하세요.')
  })

  it('길이와 상관없이 값이 있으면 통과한다', () => {
    expect(validateRequiredPassword('x')).toBeNull()
  })
})

describe('validateNewPassword', () => {
  it('최소 길이는 백엔드와 같은 8자다', () => {
    expect(MIN_PASSWORD_LENGTH).toBe(8)
  })

  it('비어 있으면 입력 안내를 돌려준다', () => {
    expect(validateNewPassword('')).toBe('비밀번호를 입력하세요.')
  })

  it('8자 미만이면 길이 안내를 돌려준다', () => {
    expect(validateNewPassword('1234567')).toBe('비밀번호는 8자 이상이어야 합니다.')
  })

  it('8자 이상이면 통과한다', () => {
    expect(validateNewPassword('12345678')).toBeNull()
  })
})
