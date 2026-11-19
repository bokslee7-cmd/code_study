import type { Task } from '../../src/services/task-service'

export function makeTask(overrides: Partial<Task> = {}): Task {
  return {
    id: 't-1',
    projectId: 'p-1',
    taskNumber: 1,
    title: 'Add Todo Function',
    description: '할 일 추가 기능을 배운다',
    uploadMethod: 'file',
    isCompleted: false,
    createdAt: '2026-11-02T12:00:00Z',
    updatedAt: '2026-11-02T12:00:00Z',
    ...overrides,
  }
}

// 서버(snake_case) 응답 형태. 서비스 테스트에서 변환 결과를 확인할 때 쓴다.
export const serverTask = {
  id: 't-1',
  project_id: 'p-1',
  task_number: 1,
  title: 'Add Todo Function',
  description: '할 일 추가 기능을 배운다',
  upload_method: 'file',
  is_completed: false,
  created_at: '2026-11-02T12:00:00Z',
  updated_at: '2026-11-02T12:00:00Z',
}
