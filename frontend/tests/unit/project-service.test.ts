import { ApiError, apiClient } from '../../src/services/api-client'
import {
  createProject,
  deleteProject,
  getProject,
  listProjects,
  updateProject,
} from '../../src/services/project-service'
import { serverProject } from '../fixtures/project'

const appProject = {
  id: 'p-1',
  title: 'My Todo App',
  description: '할 일 앱을 만들며 배우는 프로젝트',
  createdAt: '2026-11-01T12:00:00Z',
  updatedAt: '2026-11-05T12:00:00Z',
  lastActivityAt: '2026-11-05T12:00:00Z',
  taskCount: 5,
  completedTaskCount: 2,
  progressPercent: 40,
}

afterEach(() => {
  vi.restoreAllMocks()
})

describe('listProjects', () => {
  it('GET /projects를 호출하고 camelCase 프로젝트 배열로 변환해 돌려준다', async () => {
    const get = vi
      .spyOn(apiClient, 'get')
      .mockResolvedValue({ data: { projects: [serverProject] } })

    const projects = await listProjects()

    expect(get).toHaveBeenCalledWith('/projects')
    expect(projects).toEqual([appProject])
  })

  it('프로젝트가 없으면 빈 배열을 돌려준다', async () => {
    vi.spyOn(apiClient, 'get').mockResolvedValue({ data: { projects: [] } })

    await expect(listProjects()).resolves.toEqual([])
  })

  it('설명이 null이면 null 그대로 둔다', async () => {
    vi.spyOn(apiClient, 'get').mockResolvedValue({
      data: { projects: [{ ...serverProject, description: null }] },
    })

    const [project] = await listProjects()

    expect(project.description).toBeNull()
  })

  it('서버 오류(ApiError)는 그대로 던진다', async () => {
    const error = new ApiError({ code: 'unauthorized', message: '로그인 필요', status: 401 })
    vi.spyOn(apiClient, 'get').mockRejectedValue(error)

    await expect(listProjects()).rejects.toBe(error)
  })
})

describe('getProject', () => {
  it('GET /projects/{id}를 호출하고 변환해 돌려준다', async () => {
    const get = vi.spyOn(apiClient, 'get').mockResolvedValue({ data: serverProject })

    const project = await getProject('p-1')

    expect(get).toHaveBeenCalledWith('/projects/p-1')
    expect(project).toEqual(appProject)
  })

  it('403/404 같은 서버 오류는 그대로 던진다', async () => {
    const error = new ApiError({ code: 'not_found', message: '없는 프로젝트', status: 404 })
    vi.spyOn(apiClient, 'get').mockRejectedValue(error)

    await expect(getProject('p-9')).rejects.toBe(error)
  })
})

describe('createProject', () => {
  it('POST /projects에 제목과 설명을 보내고 변환한 프로젝트를 돌려준다', async () => {
    const post = vi.spyOn(apiClient, 'post').mockResolvedValue({ data: serverProject })

    const project = await createProject({ title: 'My Todo App', description: '설명' })

    expect(post).toHaveBeenCalledWith('/projects', { title: 'My Todo App', description: '설명' })
    expect(project).toEqual(appProject)
  })

  it('검증 오류(400)는 그대로 던진다', async () => {
    const error = new ApiError({
      code: 'validation_error',
      message: '제목을 확인하세요.',
      status: 400,
      details: { field: 'title' },
    })
    vi.spyOn(apiClient, 'post').mockRejectedValue(error)

    await expect(createProject({ title: ' ', description: null })).rejects.toBe(error)
  })
})

describe('updateProject', () => {
  it('PATCH /projects/{id}에 바꿀 필드만 보내고 변환해 돌려준다', async () => {
    const patch = vi.spyOn(apiClient, 'patch').mockResolvedValue({ data: serverProject })

    const project = await updateProject('p-1', { title: '새 제목' })

    expect(patch).toHaveBeenCalledWith('/projects/p-1', { title: '새 제목' })
    expect(project).toEqual(appProject)
  })
})

describe('deleteProject', () => {
  it('DELETE /projects/{id}를 호출하고 아무것도 돌려주지 않는다', async () => {
    const del = vi.spyOn(apiClient, 'delete').mockResolvedValue({ data: undefined })

    await expect(deleteProject('p-1')).resolves.toBeUndefined()

    expect(del).toHaveBeenCalledWith('/projects/p-1')
  })
})
