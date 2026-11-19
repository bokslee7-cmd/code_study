import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import CreateProjectModal, {
  type CreateProjectValues,
} from '@/components/project/CreateProjectModal'
import ProjectCard from '@/components/project/ProjectCard'
import { Button } from '@/components/ui/button'
import { ApiError } from '@/services/api-client'
import { createProject, listProjects } from '@/services/project-service'

const LOAD_ERROR_MESSAGE = '프로젝트를 불러오지 못했습니다. 잠시 후 다시 시도하세요.'

export default function Dashboard() {
  const queryClient = useQueryClient()
  const [isCreating, setIsCreating] = useState(false)
  const {
    data: projects,
    isPending,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: ['projects'],
    queryFn: listProjects,
  })
  const createMutation = useMutation({
    mutationFn: (values: CreateProjectValues) => createProject(values),
    // 목록을 다시 불러오는 동안 대화상자가 제출 중 상태로 남아, 닫힌 뒤에는 새 프로젝트가 이미 보인다.
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['projects'] }),
  })

  async function handleCreate(values: CreateProjectValues): Promise<void> {
    await createMutation.mutateAsync(values)
  }

  return (
    <main className="mx-auto w-full max-w-5xl p-4">
      <div className="mb-4 flex items-center justify-between gap-2">
        <h1 className="text-2xl font-semibold">대시보드</h1>
        <Button onClick={() => setIsCreating(true)}>새 프로젝트</Button>
      </div>
      {isPending && <p role="status">프로젝트를 불러오는 중입니다...</p>}
      {isError && (
        <div role="alert" className="flex flex-col items-start gap-2 text-sm text-destructive">
          <p>{error instanceof ApiError ? error.message : LOAD_ERROR_MESSAGE}</p>
          <Button variant="outline" onClick={() => void refetch()}>
            다시 시도
          </Button>
        </div>
      )}
      {projects?.length === 0 && (
        <div className="flex flex-col items-start gap-3">
          <p className="text-muted-foreground">아직 프로젝트가 없습니다.</p>
          <Button onClick={() => setIsCreating(true)}>첫 프로젝트 만들기</Button>
        </div>
      )}
      {projects && projects.length > 0 && (
        <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {projects.map((project) => (
            <li key={project.id}>
              <ProjectCard project={project} />
            </li>
          ))}
        </ul>
      )}
      {isCreating && (
        <CreateProjectModal onSubmit={handleCreate} onClose={() => setIsCreating(false)} />
      )}
    </main>
  )
}
