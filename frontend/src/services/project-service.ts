import { apiClient } from './api-client'

export interface Project {
  id: string
  title: string
  description: string | null
  createdAt: string
  updatedAt: string
  lastActivityAt: string
  taskCount: number
  completedTaskCount: number
  progressPercent: number
}

export interface CreateProjectInput {
  title: string
  description?: string | null
}

export interface UpdateProjectInput {
  title?: string
  description?: string | null
}

interface ProjectDto {
  id: string
  title: string
  description: string | null
  created_at: string
  updated_at: string
  last_activity_at: string
  task_count: number
  completed_task_count: number
  progress_percent: number
}

function toProject(dto: ProjectDto): Project {
  return {
    id: dto.id,
    title: dto.title,
    description: dto.description,
    createdAt: dto.created_at,
    updatedAt: dto.updated_at,
    lastActivityAt: dto.last_activity_at,
    taskCount: dto.task_count,
    completedTaskCount: dto.completed_task_count,
    progressPercent: dto.progress_percent,
  }
}

export async function listProjects(): Promise<Project[]> {
  const { data } = await apiClient.get<{ projects: ProjectDto[] }>('/projects')
  return data.projects.map(toProject)
}

export async function getProject(projectId: string): Promise<Project> {
  const { data } = await apiClient.get<ProjectDto>(`/projects/${projectId}`)
  return toProject(data)
}

export async function createProject(input: CreateProjectInput): Promise<Project> {
  const { data } = await apiClient.post<ProjectDto>('/projects', input)
  return toProject(data)
}

export async function updateProject(
  projectId: string,
  input: UpdateProjectInput,
): Promise<Project> {
  const { data } = await apiClient.patch<ProjectDto>(`/projects/${projectId}`, input)
  return toProject(data)
}

export async function deleteProject(projectId: string): Promise<void> {
  await apiClient.delete(`/projects/${projectId}`)
}
