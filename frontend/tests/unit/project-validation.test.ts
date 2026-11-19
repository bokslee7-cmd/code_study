import { MAX_PROJECT_TITLE_LENGTH, validateProjectTitle } from '../../src/lib/project-validation'

describe('validateProjectTitle', () => {
  it.each(['a', 'My Todo App', '  앞뒤 공백 포함  '])('"%s"는 통과한다', (title) => {
    expect(validateProjectTitle(title)).toBeNull()
  })

  it('비어 있거나 공백뿐이면 입력 안내를 돌려준다', () => {
    expect(validateProjectTitle('')).toBe('프로젝트 제목을 입력하세요.')
    expect(validateProjectTitle('   ')).toBe('프로젝트 제목을 입력하세요.')
  })

  it('공백을 뺀 길이가 255자면 통과하고 256자면 길이 안내를 돌려준다', () => {
    expect(MAX_PROJECT_TITLE_LENGTH).toBe(255)
    expect(validateProjectTitle(` ${'가'.repeat(255)} `)).toBeNull()
    expect(validateProjectTitle('가'.repeat(256))).toBe('프로젝트 제목은 255자 이하로 입력하세요.')
  })
})
