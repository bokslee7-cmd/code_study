import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { ApiError } from '@/services/api-client'
import { useDocument } from '@/services/document-service'
import type { LinePosition } from '@/types/document'
import CodePanel from './CodePanel'
import ExplanationPanel from './ExplanationPanel'
import GenerationProgress from './GenerationProgress'

const LOAD_ERROR_MESSAGE = '문서를 불러오지 못했습니다. 잠시 후 다시 시도하세요.'
const PARTIAL_FAILURE_MESSAGE = '일부 섹션을 만들지 못했습니다. 질문하기로 보충할 수 있어요.'

// 줄을 가리킨 쪽(source)에 따라 상대 패널만 반응하게 해 서로 되돌려 보내는 일을 막는다.
interface LineSync {
  position: LinePosition
  source: 'code' | 'explanation'
}

export default function DocumentViewer({ taskId }: { taskId: string }) {
  const { document, status, estimatedRemainingSeconds, isPending, isError, error, refetch } =
    useDocument(taskId)
  const [sync, setSync] = useState<LineSync | null>(null)

  if (isPending) return <p role="status">문서를 불러오는 중입니다...</p>

  if (isError) {
    return (
      <div role="alert" className="flex flex-col items-start gap-2 text-sm text-destructive">
        <p>{error instanceof ApiError ? error.message : LOAD_ERROR_MESSAGE}</p>
        <Button variant="outline" onClick={() => void refetch()}>
          다시 시도
        </Button>
      </div>
    )
  }

  // isPending·isError를 지난 뒤의 undefined는 없으므로 여기서 null(문서 없음)만 남는다.
  if (!document) {
    return <p className="text-sm text-muted-foreground">아직 문서가 없습니다.</p>
  }

  if (status === 'pending' || status === 'in_progress') {
    return (
      <GenerationProgress status={status} estimatedRemainingSeconds={estimatedRemainingSeconds} />
    )
  }

  if (status === 'failed') {
    return (
      <div
        role="alert"
        className="flex flex-col items-start gap-2 rounded-lg border border-red-300 bg-red-50 p-4 text-sm text-red-900"
      >
        <p className="font-medium">문서를 만들지 못했습니다.</p>
        <p>사유: {document.generationError ?? '알 수 없는 오류'}</p>
        <p>
          잠시 후 다시 시도해 주세요. 문제가 계속되면 코드를 다시 올려 새 태스크로 만들어 보세요.
        </p>
        <Button variant="outline" onClick={() => void refetch()}>
          다시 확인
        </Button>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-3">
      {document.failedChapters.length > 0 && (
        <p
          role="status"
          className="rounded-lg border border-yellow-300 bg-yellow-50 p-3 text-sm text-yellow-900"
        >
          {PARTIAL_FAILURE_MESSAGE}
        </p>
      )}
      <div className="grid gap-4 lg:grid-cols-2">
        <section aria-label="코드">
          <CodePanel
            files={document.files}
            highlight={sync?.source === 'explanation' ? sync.position : null}
            onVisibleLineChange={(position) => setSync({ position, source: 'code' })}
          />
        </section>
        <section aria-label="설명">
          <ExplanationPanel
            content={document.content}
            failedChapters={document.failedChapters}
            activeLine={sync?.position ?? null}
            scrollTarget={sync?.source === 'code' ? sync.position : null}
            onLineSelect={(position) => setSync({ position, source: 'explanation' })}
          />
        </section>
      </div>
    </div>
  )
}
