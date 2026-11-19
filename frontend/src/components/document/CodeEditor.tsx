import Editor, { type OnMount } from '@monaco-editor/react'
import { useEffect, useRef, useState } from 'react'
import { MONACO_OPTIONS, toMonacoLanguage } from '@/lib/monaco-config'

type StandaloneEditor = Parameters<OnMount>[0]

// 강조 줄로 이동하며 생기는 스크롤 이벤트는 사용자가 스크롤한 것이 아니므로 잠시 무시한다.
const PROGRAMMATIC_SCROLL_WINDOW_MS = 300

interface CodeEditorProps {
  value: string
  language: string
  path?: string
  highlightLine?: number | null
  onTopLineChange?: (line: number) => void
}

// Monaco를 감싼 얇은 래퍼. 테스트에서는 '@monaco-editor/react'를 모킹해 대체한다.
export default function CodeEditor({
  value,
  language,
  path,
  highlightLine = null,
  onTopLineChange,
}: CodeEditorProps) {
  const [editor, setEditor] = useState<StandaloneEditor | null>(null)
  const onTopLineChangeRef = useRef(onTopLineChange)
  const ignoreScrollRef = useRef(false)

  useEffect(() => {
    onTopLineChangeRef.current = onTopLineChange
  }, [onTopLineChange])

  useEffect(() => {
    if (!editor) return
    const subscription = editor.onDidScrollChange(() => {
      if (ignoreScrollRef.current) {
        ignoreScrollRef.current = false
        return
      }
      const range = editor.getVisibleRanges()[0]
      if (range) onTopLineChangeRef.current?.(range.startLineNumber)
    })
    return () => subscription.dispose()
  }, [editor])

  useEffect(() => {
    if (!editor || highlightLine === null) return
    const decorations = editor.createDecorationsCollection([
      {
        range: {
          startLineNumber: highlightLine,
          startColumn: 1,
          endLineNumber: highlightLine,
          endColumn: 1,
        },
        options: { isWholeLine: true, className: 'document-highlight-line' },
      },
    ])
    ignoreScrollRef.current = true
    const timer = setTimeout(() => {
      ignoreScrollRef.current = false
    }, PROGRAMMATIC_SCROLL_WINDOW_MS)
    editor.revealLineInCenter(highlightLine)
    return () => {
      clearTimeout(timer)
      decorations.clear()
    }
  }, [editor, highlightLine])

  return (
    <Editor
      value={value}
      language={toMonacoLanguage(language)}
      path={path}
      options={MONACO_OPTIONS}
      loading="코드 편집기를 불러오는 중..."
      onMount={(mountedEditor) => setEditor(mountedEditor)}
    />
  )
}
