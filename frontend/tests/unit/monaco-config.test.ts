import { MONACO_OPTIONS, toMonacoLanguage } from '../../src/lib/monaco-config'

describe('MONACO_OPTIONS', () => {
  it('읽기 전용이고 수정할 수 없는 뷰어 설정이다', () => {
    expect(MONACO_OPTIONS.readOnly).toBe(true)
    expect(MONACO_OPTIONS.domReadOnly).toBe(true)
  })

  it('긴 줄은 접고 레이아웃을 컨테이너에 맞춘다', () => {
    expect(MONACO_OPTIONS.wordWrap).toBe('on')
    expect(MONACO_OPTIONS.automaticLayout).toBe(true)
    expect(MONACO_OPTIONS.minimap).toEqual({ enabled: false })
  })
})

describe('toMonacoLanguage', () => {
  it('대소문자를 무시하고 Monaco 언어 id로 바꾼다', () => {
    expect(toMonacoLanguage('Python')).toBe('python')
  })

  it.each([
    ['js', 'javascript'],
    ['ts', 'typescript'],
    ['py', 'python'],
    ['c++', 'cpp'],
    ['c#', 'csharp'],
  ])('별칭 %s는 %s로 바꾼다', (alias, expected) => {
    expect(toMonacoLanguage(alias)).toBe(expected)
  })

  it('비어 있으면 plaintext로 둔다', () => {
    expect(toMonacoLanguage('')).toBe('plaintext')
  })
})
