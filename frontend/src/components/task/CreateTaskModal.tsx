import { useState, type FormEvent } from 'react'
import { Dialog, Tabs } from 'radix-ui'
import FormField from '@/components/auth/FormField'
import { useSubmitState } from '@/components/auth/useSubmitState'
import FileUpload from '@/components/upload/FileUpload'
import FolderUpload from '@/components/upload/FolderUpload'
import PasteCode, { type PasteCodeValue } from '@/components/upload/PasteCode'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import {
  validatePaste,
  validateTaskDescription,
  validateTaskTitle,
  validateUploadFiles,
} from '@/lib/upload-validation'
import type { CreateTaskInput, UploadMethod } from '@/services/task-service'

interface CreateTaskModalProps {
  onSubmit: (input: CreateTaskInput) => Promise<void>
  onClose: () => void
}

const METHOD_LABELS: Record<UploadMethod, string> = {
  file: '파일',
  folder: '폴더',
  paste: '코드 붙여넣기',
}
const METHODS = Object.keys(METHOD_LABELS) as UploadMethod[]

// 포커스 이동·가두기·ESC·배경 스크린리더 숨김은 Radix Dialog가, 탭 접근성은 Radix Tabs가 처리한다.
export default function CreateTaskModal({ onSubmit, onClose }: CreateTaskModalProps) {
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [method, setMethod] = useState<UploadMethod>('file')
  const [files, setFiles] = useState<File[]>([])
  const [folderFiles, setFolderFiles] = useState<File[]>([])
  const [paste, setPaste] = useState<PasteCodeValue>({ code: '', language: '' })
  const [titleError, setTitleError] = useState<string | null>(null)
  const [descriptionError, setDescriptionError] = useState<string | null>(null)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [opener] = useState(() => document.activeElement)

  async function createAndClose(input: CreateTaskInput) {
    await onSubmit(input)
    onClose()
  }

  const { isPending, serverError, submit } = useSubmitState(createAndClose)

  function uploadValidationError(): string | null {
    if (method === 'file') return validateUploadFiles(files)
    if (method === 'folder') return validateUploadFiles(folderFiles)
    return validatePaste(paste.code, paste.language)
  }

  function buildInput(): CreateTaskInput {
    const base = {
      title: title.trim(),
      description: description.trim() || null,
      uploadMethod: method,
    }
    if (method === 'paste') return { ...base, code: paste.code, language: paste.language }
    return { ...base, files: method === 'file' ? files : folderFiles }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (isPending) return
    const nextTitleError = validateTaskTitle(title)
    const nextDescriptionError = validateTaskDescription(description)
    const nextUploadError = uploadValidationError()
    setTitleError(nextTitleError)
    setDescriptionError(nextDescriptionError)
    setUploadError(nextUploadError)
    if (nextTitleError || nextDescriptionError || nextUploadError) return

    await submit(buildInput())
  }

  function keepOpenWhilePending(event: Event) {
    if (isPending) event.preventDefault()
  }

  // Radix는 Dialog.Trigger로만 포커스를 돌려주는데 여기서는 Trigger 없이 열기 때문에 직접 돌려준다.
  function restoreFocusToOpener(event: Event) {
    event.preventDefault()
    if (opener instanceof HTMLElement) opener.focus()
  }

  return (
    <Dialog.Root open onOpenChange={(open) => !open && onClose()}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-black/50" />
        <Dialog.Content
          aria-modal="true"
          aria-describedby={undefined}
          onEscapeKeyDown={keepOpenWhilePending}
          onInteractOutside={keepOpenWhilePending}
          onCloseAutoFocus={restoreFocusToOpener}
          className="fixed top-1/2 left-1/2 z-50 max-h-[90vh] w-[calc(100%-2rem)] max-w-lg -translate-x-1/2 -translate-y-1/2 overflow-y-auto rounded-xl bg-background p-4 ring-1 ring-foreground/10"
        >
          <Dialog.Title className="mb-4 text-lg font-semibold">새 태스크 만들기</Dialog.Title>
          <form noValidate onSubmit={handleSubmit} className="flex flex-col gap-4">
            <FormField
              id="create-task-title"
              label="태스크 제목"
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              error={titleError}
            />
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="create-task-description">설명 (선택)</Label>
              <Textarea
                id="create-task-description"
                value={description}
                aria-invalid={descriptionError ? true : undefined}
                onChange={(event) => setDescription(event.target.value)}
              />
              {descriptionError && <p className="text-sm text-destructive">{descriptionError}</p>}
            </div>
            <Tabs.Root value={method} onValueChange={(value) => setMethod(value as UploadMethod)}>
              <Tabs.List aria-label="코드 업로드 방식" className="mb-3 flex gap-1">
                {METHODS.map((value) => (
                  <Tabs.Trigger
                    key={value}
                    value={value}
                    disabled={isPending}
                    className="rounded-lg border px-3 py-1.5 text-sm data-[state=active]:bg-primary data-[state=active]:text-primary-foreground"
                  >
                    {METHOD_LABELS[value]}
                  </Tabs.Trigger>
                ))}
              </Tabs.List>
              <Tabs.Content value="file">
                <FileUpload files={files} onChange={setFiles} disabled={isPending} />
              </Tabs.Content>
              <Tabs.Content value="folder">
                <FolderUpload files={folderFiles} onChange={setFolderFiles} disabled={isPending} />
              </Tabs.Content>
              <Tabs.Content value="paste">
                <PasteCode value={paste} onChange={setPaste} disabled={isPending} />
              </Tabs.Content>
            </Tabs.Root>
            {uploadError && (
              <p role="alert" className="text-sm text-destructive">
                {uploadError}
              </p>
            )}
            {serverError && (
              <p role="alert" className="text-sm text-destructive">
                {serverError}
              </p>
            )}
            <div className="flex justify-end gap-2">
              <Button type="button" variant="outline" onClick={onClose} disabled={isPending}>
                취소
              </Button>
              <Button type="submit" disabled={isPending}>
                {isPending ? '만드는 중...' : '태스크 만들기'}
              </Button>
            </div>
          </form>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}
