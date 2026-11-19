import { useQuery } from '@tanstack/react-query'
import { Tabs } from 'radix-ui'
import { Link, useParams } from 'react-router-dom'
import DocumentViewer from '@/components/document/DocumentViewer'
import { Button } from '@/components/ui/button'
import { formatDate } from '@/lib/format-date'
import { ApiError } from '@/services/api-client'
import { getTask } from '@/services/task-service'

const LOAD_ERROR_MESSAGE = '태스크를 불러오지 못했습니다. 잠시 후 다시 시도하세요.'
const FORBIDDEN_MESSAGE = '이 태스크에 접근할 권한이 없습니다.'
const NOT_FOUND_MESSAGE = '태스크를 찾을 수 없습니다. 삭제되었거나 주소가 잘못되었을 수 있습니다.'

const HTTP_FORBIDDEN = 403
const HTTP_NOT_FOUND = 404

// 문서 탭은 DocumentViewer가 채운다. 연습문제(Phase 7)·Q&A(Phase 8)는 아직 준비 중이다.
const TABS = [
  { value: 'document', label: '문서' },
  { value: 'practice', label: '연습문제', placeholder: '연습문제는 준비 중입니다.' },
  { value: 'qa', label: 'Q&A', placeholder: 'Q&A는 준비 중입니다.' },
]

function errorMessage(error: unknown): string {
  if (!(error instanceof ApiError)) return LOAD_ERROR_MESSAGE
  if (error.status === HTTP_FORBIDDEN) return FORBIDDEN_MESSAGE
  if (error.status === HTTP_NOT_FOUND) return NOT_FOUND_MESSAGE
  return error.message
}

// 권한·존재 여부는 다시 시도해도 결과가 같으므로 재시도 버튼을 보여주지 않는다.
function isRetryable(error: unknown): boolean {
  return !(
    error instanceof ApiError &&
    (error.status === HTTP_FORBIDDEN || error.status === HTTP_NOT_FOUND)
  )
}

export default function TaskDetail() {
  const { projectId = '', taskId = '' } = useParams()
  const {
    data: task,
    isPending,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: ['projects', projectId, 'tasks', taskId],
    queryFn: () => getTask(taskId),
  })

  return (
    <main className="mx-auto w-full max-w-6xl p-4">
      <Link to={`/projects/${projectId}`} className="mb-4 inline-block text-sm underline">
        프로젝트로 돌아가기
      </Link>
      {isPending && <p role="status">태스크를 불러오는 중입니다...</p>}
      {isError && (
        <div role="alert" className="flex flex-col items-start gap-2 text-sm text-destructive">
          <p>{errorMessage(error)}</p>
          {isRetryable(error) && (
            <Button variant="outline" onClick={() => void refetch()}>
              다시 시도
            </Button>
          )}
        </div>
      )}
      {task && (
        <>
          <p className="text-sm text-muted-foreground">Task {task.taskNumber}</p>
          <h1 className="text-2xl font-semibold">{task.title}</h1>
          {task.description && <p className="mt-1 text-muted-foreground">{task.description}</p>}
          <p className="mt-2 text-xs text-muted-foreground">생성일: {formatDate(task.createdAt)}</p>
          <Tabs.Root defaultValue="document" className="mt-6">
            <Tabs.List aria-label="태스크 학습 영역" className="mb-3 flex gap-1">
              {TABS.map((tab) => (
                <Tabs.Trigger
                  key={tab.value}
                  value={tab.value}
                  className="rounded-lg border px-3 py-1.5 text-sm data-[state=active]:bg-primary data-[state=active]:text-primary-foreground"
                >
                  {tab.label}
                </Tabs.Trigger>
              ))}
            </Tabs.List>
            {TABS.map((tab) => (
              <Tabs.Content key={tab.value} value={tab.value}>
                {tab.value === 'document' ? (
                  <DocumentViewer taskId={taskId} />
                ) : (
                  <p className="text-sm text-muted-foreground">{tab.placeholder}</p>
                )}
              </Tabs.Content>
            ))}
          </Tabs.Root>
        </>
      )}
    </main>
  )
}
