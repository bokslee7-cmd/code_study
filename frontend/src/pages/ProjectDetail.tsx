import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useNavigate, useParams } from 'react-router-dom'
import ProjectProgress from '@/components/project/ProjectProgress'
import CreateTaskModal from '@/components/task/CreateTaskModal'
import TaskCard from '@/components/task/TaskCard'
import { Button } from '@/components/ui/button'
import { formatDate } from '@/lib/format-date'
import { ApiError } from '@/services/api-client'
import { getProject } from '@/services/project-service'
import { createTask, listTasks, type CreateTaskInput } from '@/services/task-service'

const LOAD_ERROR_MESSAGE = '프로젝트를 불러오지 못했습니다. 잠시 후 다시 시도하세요.'
const TASKS_LOAD_ERROR_MESSAGE = '태스크를 불러오지 못했습니다. 잠시 후 다시 시도하세요.'
const FORBIDDEN_MESSAGE = '이 프로젝트에 접근할 권한이 없습니다.'
const NOT_FOUND_MESSAGE = '프로젝트를 찾을 수 없습니다. 삭제되었거나 주소가 잘못되었을 수 있습니다.'

const HTTP_FORBIDDEN = 403
const HTTP_NOT_FOUND = 404

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

function TaskTimeline({ projectId }: { projectId: string }) {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [isCreating, setIsCreating] = useState(false)
  const {
    data: tasks,
    isPending,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: ['projects', projectId, 'tasks'],
    queryFn: () => listTasks(projectId),
  })
  const createMutation = useMutation({
    mutationFn: (input: CreateTaskInput) => createTask(projectId, input),
    // 프로젝트 정보(태스크 수·진행률)와 목록이 모두 바뀌므로 ["projects"] 아래를 한 번에 무효화한다.
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['projects'] }),
  })

  async function handleCreate(input: CreateTaskInput): Promise<void> {
    const task = await createMutation.mutateAsync(input)
    navigate(`/projects/${projectId}/tasks/${task.id}`)
  }

  return (
    <section>
      <div className="mb-2 flex items-center justify-between gap-2">
        <h2 className="text-lg font-semibold">태스크 타임라인</h2>
        <Button onClick={() => setIsCreating(true)}>새 태스크</Button>
      </div>
      {isPending && <p role="status">태스크를 불러오는 중입니다...</p>}
      {isError && (
        <div role="alert" className="flex flex-col items-start gap-2 text-sm text-destructive">
          <p>{error instanceof ApiError ? error.message : TASKS_LOAD_ERROR_MESSAGE}</p>
          <Button variant="outline" onClick={() => void refetch()}>
            다시 시도
          </Button>
        </div>
      )}
      {tasks?.length === 0 && (
        <p className="text-sm text-muted-foreground">
          아직 태스크가 없습니다. 첫 태스크를 만들어 보세요.
        </p>
      )}
      {tasks && tasks.length > 0 && (
        <ul className="flex flex-col gap-3">
          {tasks.map((task) => (
            <li key={task.id}>
              <TaskCard task={task} />
            </li>
          ))}
        </ul>
      )}
      {isCreating && (
        <CreateTaskModal onSubmit={handleCreate} onClose={() => setIsCreating(false)} />
      )}
    </section>
  )
}

export default function ProjectDetail() {
  const { projectId = '' } = useParams()
  const {
    data: project,
    isPending,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: ['projects', projectId],
    queryFn: () => getProject(projectId),
  })

  return (
    <main className="mx-auto w-full max-w-3xl p-4">
      <Link to="/dashboard" className="mb-4 inline-block text-sm underline">
        대시보드로 돌아가기
      </Link>
      {isPending && <p role="status">프로젝트를 불러오는 중입니다...</p>}
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
      {project && (
        <>
          <h1 className="text-2xl font-semibold">{project.title}</h1>
          <p className="mt-1 text-muted-foreground">{project.description ?? '설명이 없습니다.'}</p>
          <p className="mt-2 text-xs text-muted-foreground">
            생성일: {formatDate(project.createdAt)}
          </p>
          <div className="my-6">
            <ProjectProgress
              completedTaskCount={project.completedTaskCount}
              taskCount={project.taskCount}
              progressPercent={project.progressPercent}
            />
          </div>
          <TaskTimeline projectId={projectId} />
        </>
      )}
    </main>
  )
}
