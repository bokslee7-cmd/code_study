import type { editor } from 'monaco-editor'

// 코드를 읽기만 하는 뷰어라서 수정·커서 깜빡임 같은 편집 기능은 모두 끈다.
export const MONACO_OPTIONS: editor.IStandaloneEditorConstructionOptions = {
  readOnly: true,
  domReadOnly: true,
  wordWrap: 'on',
  automaticLayout: true,
  minimap: { enabled: false },
  scrollBeyondLastLine: false,
  renderLineHighlight: 'none',
  fontSize: 14,
}

const LANGUAGE_ALIASES: Record<string, string> = {
  js: 'javascript',
  ts: 'typescript',
  py: 'python',
  'c++': 'cpp',
  'c#': 'csharp',
}

// 서버가 주는 언어 이름을 Monaco 언어 id로 바꾼다.
export function toMonacoLanguage(language: string): string {
  const normalized = language.trim().toLowerCase()
  if (normalized === '') return 'plaintext'
  return LANGUAGE_ALIASES[normalized] ?? normalized
}
