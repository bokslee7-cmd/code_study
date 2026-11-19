import { apiClient } from './api-client'

export type UploadMethod = 'file' | 'folder' | 'paste'

export interface Task {
  id: string
  projectId: string
  taskNumber: number
  title: string
  description: string | null
  uploadMethod: UploadMethod | null
  isCompleted: boolean
  createdAt: string
  updatedAt: string
}

export interface CreateTaskInput {
  title: string
  description?: string | null
  uploadMethod: UploadMethod
  // file/folder: 선택한 파일. folder는 File.webkitRelativePath를 파일 이름으로 보낸다.
  files?: File[]
  // paste: 붙여넣은 코드와 언어
  code?: string
  language?: string
}

export interface UpdateTaskInput {
  title?: string
  description?: string | null
}

interface TaskDto {
  id: string
  project_id: string
  task_number: number
  title: string
  description: string | null
  upload_method: UploadMethod | null
  is_completed?: boolean
  created_at: string
  updated_at: string
}

function toTask(dto: TaskDto): Task {
  return {
    id: dto.id,
    projectId: dto.project_id,
    taskNumber: dto.task_number,
    title: dto.title,
    description: dto.description,
    uploadMethod: dto.upload_method,
    isCompleted: dto.is_completed ?? false,
    createdAt: dto.created_at,
    updatedAt: dto.updated_at,
  }
}

function toFormData(input: CreateTaskInput): FormData {
  const form = new FormData()
  form.append('title', input.title)
  if (input.description) form.append('description', input.description)
  form.append('upload_method', input.uploadMethod)
  for (const file of input.files ?? []) {
    // 폴더 업로드는 서버가 파일 이름 자리에 담긴 상대 경로로 폴더 구조를 복원한다.
    if (input.uploadMethod === 'folder') form.append('files', file, file.webkitRelativePath)
    else form.append('files', file)
  }
  if (input.uploadMethod === 'paste') {
    form.append('code', input.code ?? '')
    form.append('language', input.language ?? '')
  }
  return form
}

export async function listTasks(projectId: string): Promise<Task[]> {
  const { data } = await apiClient.get<{ tasks: TaskDto[] }>(`/projects/${projectId}/tasks`)
  return data.tasks.map(toTask)
}

export async function getTask(taskId: string): Promise<Task> {
  const { data } = await apiClient.get<TaskDto>(`/tasks/${taskId}`)
  return toTask(data)
}

// multipart/form-data. Content-Type은 브라우저(axios)가 boundary와 함께 정하도록 직접 지정하지 않는다.
export async function createTask(projectId: string, input: CreateTaskInput): Promise<Task> {
  const { data } = await apiClient.post<TaskDto>(`/projects/${projectId}/tasks`, toFormData(input))
  return toTask(data)
}

export async function updateTask(taskId: string, input: UpdateTaskInput): Promise<Task> {
  const { data } = await apiClient.patch<TaskDto>(`/tasks/${taskId}`, input)
  return toTask(data)
}

export async function deleteTask(taskId: string): Promise<void> {
  await apiClient.delete(`/tasks/${taskId}`)
}
