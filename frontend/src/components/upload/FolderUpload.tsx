import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { isExcludedPath, validateUploadFiles } from '@/lib/upload-validation'

interface FolderUploadProps {
  files: File[]
  onChange: (files: File[]) => void
  disabled?: boolean
}

// 폴더 구조는 File.webkitRelativePath로 보존한다. 선택할 때마다 이전 선택을 대체한다.
export default function FolderUpload({ files, onChange, disabled = false }: FolderUploadProps) {
  const [error, setError] = useState<string | null>(null)
  const [excludedCount, setExcludedCount] = useState(0)

  function selectFolder(selected: File[]) {
    const kept = selected.filter((file) => !isExcludedPath(file.webkitRelativePath))
    setExcludedCount(selected.length - kept.length)
    const validationError = validateUploadFiles(kept)
    setError(validationError)
    if (!validationError) onChange(kept)
  }

  function clear() {
    setError(null)
    setExcludedCount(0)
    onChange([])
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-col items-center gap-2 rounded-lg border border-dashed p-6 text-sm text-muted-foreground">
        <p>폴더를 선택하면 폴더 구조를 유지한 채 올라갑니다.</p>
        <label className="cursor-pointer rounded-lg border px-3 py-1.5 text-foreground focus-within:ring-3 focus-within:ring-ring/50">
          폴더 선택
          <input
            type="file"
            multiple
            // React 타입에 없는 비표준 속성이지만 Chromium·Firefox·Safari가 지원한다.
            {...{ webkitdirectory: '' }}
            disabled={disabled}
            className="sr-only"
            onChange={(event) => {
              selectFolder(Array.from(event.target.files ?? []))
              event.target.value = ''
            }}
          />
        </label>
      </div>
      {excludedCount > 0 && (
        <p role="status" className="text-sm text-muted-foreground">
          {excludedCount}개 항목은 자동으로 제외했습니다. (.git, node_modules, __pycache__,
          .DS_Store)
        </p>
      )}
      {error && (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      )}
      {files.length > 0 && (
        <>
          <ul className="flex flex-col gap-1 text-sm">
            {files.map((file) => (
              <li key={file.webkitRelativePath} className="truncate">
                {file.webkitRelativePath}
              </li>
            ))}
          </ul>
          <Button type="button" variant="outline" size="sm" disabled={disabled} onClick={clear}>
            선택 지우기
          </Button>
        </>
      )}
    </div>
  )
}
