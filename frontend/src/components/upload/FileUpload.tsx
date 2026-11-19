import { useState, type DragEvent } from 'react'
import { Button } from '@/components/ui/button'
import { validateUploadFiles } from '@/lib/upload-validation'

interface FileUploadProps {
  files: File[]
  onChange: (files: File[]) => void
  disabled?: boolean
}

function isSameFile(a: File, b: File): boolean {
  return a.name === b.name && a.size === b.size && a.lastModified === b.lastModified
}

// 끌어다 놓기와 파일 선택을 모두 지원한다. 검증을 통과하지 못하면 선택을 바꾸지 않고 오류만 보여준다.
export default function FileUpload({ files, onChange, disabled = false }: FileUploadProps) {
  const [error, setError] = useState<string | null>(null)

  function addFiles(incoming: File[]) {
    const added = incoming.filter((file) => !files.some((existing) => isSameFile(existing, file)))
    const next = [...files, ...added]
    const validationError = validateUploadFiles(next)
    setError(validationError)
    if (!validationError) onChange(next)
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault()
    if (disabled) return
    addFiles(Array.from(event.dataTransfer.files))
  }

  function remove(target: File) {
    setError(null)
    onChange(files.filter((file) => file !== target))
  }

  return (
    <div className="flex flex-col gap-3">
      <div
        role="group"
        aria-label="파일 끌어놓기 영역"
        onDragOver={(event) => event.preventDefault()}
        onDrop={handleDrop}
        className="flex flex-col items-center gap-2 rounded-lg border border-dashed p-6 text-sm text-muted-foreground"
      >
        <p>파일을 여기로 끌어다 놓거나 아래 버튼으로 선택하세요.</p>
        <label className="cursor-pointer rounded-lg border px-3 py-1.5 text-foreground focus-within:ring-3 focus-within:ring-ring/50">
          파일 선택
          <input
            type="file"
            multiple
            disabled={disabled}
            className="sr-only"
            onChange={(event) => {
              addFiles(Array.from(event.target.files ?? []))
              event.target.value = ''
            }}
          />
        </label>
      </div>
      {error && (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      )}
      {files.length > 0 && (
        <ul className="flex flex-col gap-1 text-sm">
          {files.map((file) => (
            <li
              key={`${file.name}-${file.size}-${file.lastModified}`}
              className="flex items-center justify-between gap-2"
            >
              <span className="truncate">{file.name}</span>
              <Button
                type="button"
                variant="outline"
                size="sm"
                disabled={disabled}
                aria-label={`${file.name} 제거`}
                onClick={() => remove(file)}
              >
                제거
              </Button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
