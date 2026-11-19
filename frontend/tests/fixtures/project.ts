import type { Project } from '../../src/services/project-service'

export function makeProject(overrides: Partial<Project> = {}): Project {
  return {
    id: 'p-1',
    title: 'My Todo App',
    description: '할 일 앱을 만들며 배우는 프로젝트',
    createdAt: '2026-11-01T12:00:00Z',
    updatedAt: '2026-11-05T12:00:00Z',
    lastActivityAt: '2026-11-05T12:00:00Z',
    taskCount: 0,
    completedTaskCount: 0,
    progressPercent: 0,
    ...overrides,
  }
}

// 서버(snake_case) 응답 형태. 서비스 테스트에서 변환 결과를 확인할 때 쓴다.
export const serverProject = {
  id: 'p-1',
  title: 'My Todo App',
  description: '할 일 앱을 만들며 배우는 프로젝트',
  created_at: '2026-11-01T12:00:00Z',
  updated_at: '2026-11-05T12:00:00Z',
  last_activity_at: '2026-11-05T12:00:00Z',
  task_count: 5,
  completed_task_count: 2,
  progress_percent: 40,
}
