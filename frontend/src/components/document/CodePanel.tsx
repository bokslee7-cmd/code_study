import { useState } from 'react'
import type { DocumentFile, LinePosition } from '@/types/document'
import CodeEditor from './CodeEditor'

interface CodePanelProps {
  files: DocumentFile[]
  // 설명에서 가리킨 줄. 다른 파일을 가리키면 그 파일 탭으로 옮겨 간다.
  highlight?: LinePosition | null
  onVisibleLineChange?: (position: LinePosition) => void
}

// highlight가 가리키는 파일이 있으면 그 파일을, 아니면 현재 선택을 유지한다.
function pathFor(files: DocumentFile[], highlight: LinePosition | null, current: string): string {
  const target = highlight?.filePath
  return target && files.some((file) => file.path === target) ? target : current
}

export default function CodePanel({
  files,
  highlight = null,
  onVisibleLineChange,
}: CodePanelProps) {
  const [selectedPath, setSelectedPath] = useState(() =>
    pathFor(files, highlight, files[0]?.path ?? ''),
  )
  const [previousHighlight, setPreviousHighlight] = useState(highlight)

  // highlight가 바뀐 렌더 안에서 탭을 맞춘다(effect 없이 상태를 동기화하는 React 권장 방식).
  if (highlight !== previousHighlight) {
    setPreviousHighlight(highlight)
    setSelectedPath(pathFor(files, highlight, selectedPath))
  }

  if (files.length === 0) {
    return <p className="text-sm text-muted-foreground">표시할 코드가 없습니다.</p>
  }

  const file = files.find((candidate) => candidate.path === selectedPath) ?? files[0]
  const highlightedHere =
    highlight !== null && (highlight.filePath === '' || highlight.filePath === file.path)

  return (
    <div className="flex h-full flex-col gap-2">
      {files.length > 1 ? (
        <div role="tablist" aria-label="코드 파일" className="flex flex-wrap gap-1">
          {files.map((candidate) => (
            <button
              key={candidate.path}
              type="button"
              role="tab"
              aria-selected={candidate.path === file.path}
              onClick={() => setSelectedPath(candidate.path)}
              className="rounded-md border px-2 py-1 text-xs aria-selected:bg-primary aria-selected:text-primary-foreground"
            >
              {candidate.path}
            </button>
          ))}
        </div>
      ) : (
        <p className="text-xs text-muted-foreground">{file.path}</p>
      )}
      <div className="min-h-80 flex-1 overflow-hidden rounded-md border">
        <CodeEditor
          value={file.content}
          language={file.language}
          path={file.path}
          highlightLine={highlightedHere ? highlight.line : null}
          onTopLineChange={(line) => onVisibleLineChange?.({ filePath: file.path, line })}
        />
      </div>
    </div>
  )
}
