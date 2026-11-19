import { useState, type FormEvent } from 'react'
import { Dialog } from 'radix-ui'
import FormField from '@/components/auth/FormField'
import { useSubmitState } from '@/components/auth/useSubmitState'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { validateProjectTitle } from '@/lib/project-validation'
import { ApiError } from '@/services/api-client'

export interface CreateProjectValues {
  title: string
  description: string | null
}

interface CreateProjectModalProps {
  onSubmit: (values: CreateProjectValues) => Promise<void>
  onClose: () => void
}

function isTitleValidationError(error: unknown): error is ApiError {
  return error instanceof ApiError && error.details?.field === 'title'
}

// 포커스 이동·가두기·ESC·배경 스크린리더 숨김은 Radix Dialog가 처리한다.
export default function CreateProjectModal({ onSubmit, onClose }: CreateProjectModalProps) {
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [titleError, setTitleError] = useState<string | null>(null)
  const [opener] = useState(() => document.activeElement)

  async function createAndClose(values: CreateProjectValues) {
    try {
      await onSubmit(values)
    } catch (error) {
      if (!isTitleValidationError(error)) throw error
      setTitleError(error.message)
      return
    }
    onClose()
  }

  const { isPending, serverError, submit } = useSubmitState(createAndClose)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (isPending) return
    const validationError = validateProjectTitle(title)
    setTitleError(validationError)
    if (validationError) return

    await submit({ title: title.trim(), description: description.trim() || null })
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
          className="fixed top-1/2 left-1/2 z-50 w-[calc(100%-2rem)] max-w-md -translate-x-1/2 -translate-y-1/2 rounded-xl bg-background p-4 ring-1 ring-foreground/10"
        >
          <Dialog.Title className="mb-4 text-lg font-semibold">새 프로젝트 만들기</Dialog.Title>
          <form noValidate onSubmit={handleSubmit} className="flex flex-col gap-4">
            <FormField
              id="create-project-title"
              label="프로젝트 제목"
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              error={titleError}
            />
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="create-project-description">설명 (선택)</Label>
              <Textarea
                id="create-project-description"
                value={description}
                onChange={(event) => setDescription(event.target.value)}
              />
            </div>
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
                {isPending ? '만드는 중...' : '만들기'}
              </Button>
            </div>
          </form>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}
