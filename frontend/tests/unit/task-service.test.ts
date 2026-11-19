import { ApiError, apiClient } from '../../src/services/api-client'
import {
  createTask,
  deleteTask,
  getTask,
  listTasks,
  updateTask,
} from '../../src/services/task-service'
import { makeFile } from '../fixtures/files'
import { makeTask, serverTask } from '../fixtures/task'

afterEach(() => {
  vi.restoreAllMocks()
})

function sentForm(post: { mock: { calls: unknown[][] } }): FormData {
  return post.mock.calls[0][1] as FormData
}

describe('listTasks', () => {
  it('GET /projects/{id}/tasks를 호출하고 camelCase 배열로 변환한다', async () => {
    const get = vi.spyOn(apiClient, 'get').mockResolvedValue({ data: { tasks: [serverTask] } })

    const tasks = await listTasks('p-1')

    expect(get).toHaveBeenCalledWith('/projects/p-1/tasks')
    expect(tasks).toEqual([makeTask()])
  })

  it('설명이 null이고 완료 필드가 없으면 null·false로 둔다', async () => {
    vi.spyOn(apiClient, 'get').mockResolvedValue({
      data: { tasks: [{ ...serverTask, is_completed: undefined, description: null }] },
    })

    const [task] = await listTasks('p-1')

    expect(task.description).toBeNull()
    expect(task.isCompleted).toBe(false)
  })

  it('서버 오류(ApiError)는 그대로 던진다', async () => {
    const error = new ApiError({ code: 'forbidden', message: '권한 없음', status: 403 })
    vi.spyOn(apiClient, 'get').mockRejectedValue(error)

    await expect(listTasks('p-1')).rejects.toBe(error)
  })
})

describe('getTask', () => {
  it('GET /tasks/{id}를 호출하고 변환한다', async () => {
    const get = vi.spyOn(apiClient, 'get').mockResolvedValue({ data: serverTask })

    await expect(getTask('t-1')).resolves.toEqual(makeTask())
    expect(get).toHaveBeenCalledWith('/tasks/t-1')
  })
})

describe('createTask', () => {
  it('파일 업로드는 multipart 필드(title, description, upload_method, files)로 보낸다', async () => {
    const post = vi.spyOn(apiClient, 'post').mockResolvedValue({ data: serverTask })
    const file = makeFile('a.py')

    const task = await createTask('p-1', {
      title: 'Add Todo Function',
      description: '설명',
      uploadMethod: 'file',
      files: [file],
    })

    expect(post.mock.calls[0][0]).toBe('/projects/p-1/tasks')
    const form = sentForm(post)
    expect(form).toBeInstanceOf(FormData)
    expect(form.get('title')).toBe('Add Todo Function')
    expect(form.get('description')).toBe('설명')
    expect(form.get('upload_method')).toBe('file')
    expect(form.getAll('files')).toEqual([file])
    expect(form.has('file_paths')).toBe(false)
    expect(form.has('code')).toBe(false)
    expect(task).toEqual(makeTask())
  })

  it('설명이 없으면 description 필드를 보내지 않는다', async () => {
    const post = vi.spyOn(apiClient, 'post').mockResolvedValue({ data: serverTask })

    await createTask('p-1', {
      title: 'Add Todo Function',
      description: null,
      uploadMethod: 'file',
      files: [makeFile('a.py')],
    })

    expect(sentForm(post).has('description')).toBe(false)
  })

  it('폴더 업로드는 상대 경로를 파일 이름으로 해서 files에 담아 보낸다', async () => {
    const post = vi.spyOn(apiClient, 'post').mockResolvedValue({ data: serverTask })
    const a = makeFile('app.py', 10, 'todo/app.py')
    const b = makeFile('util.py', 10, 'todo/lib/util.py')

    await createTask('p-1', {
      title: 'Add Todo Function',
      uploadMethod: 'folder',
      files: [a, b],
    })

    const form = sentForm(post)
    expect(form.get('upload_method')).toBe('folder')
    const sent = form.getAll('files') as File[]
    expect(sent.map((file) => file.name)).toEqual(['todo/app.py', 'todo/lib/util.py'])
    expect(form.has('file_paths')).toBe(false)
  })

  it('코드 붙여넣기는 code와 language를 보낸다', async () => {
    const post = vi.spyOn(apiClient, 'post').mockResolvedValue({ data: serverTask })

    await createTask('p-1', {
      title: 'Add Todo Function',
      uploadMethod: 'paste',
      code: 'print(1)',
      language: 'python',
    })

    const form = sentForm(post)
    expect(form.get('upload_method')).toBe('paste')
    expect(form.get('code')).toBe('print(1)')
    expect(form.get('language')).toBe('python')
    expect(form.has('files')).toBe(false)
  })

  it('서버 오류(ApiError)는 그대로 던진다', async () => {
    const error = new ApiError({ code: 'file_too_large', message: '크기 초과', status: 413 })
    vi.spyOn(apiClient, 'post').mockRejectedValue(error)

    await expect(
      createTask('p-1', {
        title: 'Add Todo Function',
        uploadMethod: 'paste',
        code: 'x',
        language: 'c',
      }),
    ).rejects.toBe(error)
  })
})

describe('updateTask', () => {
  it('PATCH /tasks/{id}에 title/description을 보내고 변환한다', async () => {
    const patch = vi.spyOn(apiClient, 'patch').mockResolvedValue({ data: serverTask })

    const task = await updateTask('t-1', { title: '새 제목입니다', description: null })

    expect(patch).toHaveBeenCalledWith('/tasks/t-1', { title: '새 제목입니다', description: null })
    expect(task).toEqual(makeTask())
  })
})

describe('deleteTask', () => {
  it('DELETE /tasks/{id}를 호출한다', async () => {
    const del = vi.spyOn(apiClient, 'delete').mockResolvedValue({ data: undefined })

    await expect(deleteTask('t-1')).resolves.toBeUndefined()
    expect(del).toHaveBeenCalledWith('/tasks/t-1')
  })
})
