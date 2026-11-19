import type {
  DocumentContent,
  DocumentFile,
  DocumentStatusInfo,
  LearningDocument,
  LineExplanation,
} from '../../src/types/document'

export function makeFile(overrides: Partial<DocumentFile> = {}): DocumentFile {
  return {
    path: 'main.py',
    language: 'python',
    content: 'def add(a, b):\n    return a + b\n',
    ...overrides,
  }
}

export function makeLineExplanation(overrides: Partial<LineExplanation> = {}): LineExplanation {
  return {
    file_path: '',
    line_number: 1,
    code: 'def add(a, b):',
    what_it_does: 'add라는 함수를 만든다',
    syntax_breakdown: 'def는 함수를 만든다는 뜻이다',
    analogy: '레시피에 이름을 붙이는 것',
    alternatives: '',
    important_notes: '',
    ...overrides,
  }
}

export function makeContent(overrides: DocumentContent = {}): DocumentContent {
  return {
    chapter1: { title: '이 코드가 하는 일', summary: '두 수를 더해 주는 코드입니다.' },
    chapter2: {
      title: '알아야 할 기본 개념',
      concepts: [
        {
          name: '함수',
          explanation: '작업을 묶어 둔 코드 덩어리',
          analogy: '레시피',
          example: 'def add(a, b): return a + b',
          use_cases: '계산을 여러 번 해야 할 때',
        },
      ],
    },
    chapter3: {
      title: '코드 구조 한눈에 보기',
      flowchart: '[시작] -> [add 호출] -> [끝]',
      file_breakdown: { 'main.py': '덧셈 함수가 들어 있는 파일' },
    },
    chapter4: {
      title: '코드 한 줄씩 완전 해부',
      explanations: [
        makeLineExplanation({ line_number: 1 }),
        makeLineExplanation({
          line_number: 2,
          code: '    return a + b',
          what_it_does: '더한 결과를 돌려준다',
          syntax_breakdown: 'return은 결과를 돌려준다는 뜻이다',
          analogy: '',
        }),
      ],
    },
    chapter5: {
      title: '실행 흐름 따라가기',
      steps: [
        {
          step_number: 1,
          action: 'add(2, 3)을 부른다',
          data_state: 'a=2, b=3',
          explanation: '재료 2와 3이 함수에 들어간다',
        },
      ],
    },
    chapter6: {
      title: '핵심 개념 정리',
      concepts: [
        {
          concept_name: '반환값',
          what_it_is: '함수가 돌려주는 결과',
          why_used: '결과를 다른 곳에서 쓰려고',
          where_applied: 'return a + b',
        },
      ],
    },
    chapter7: {
      title: '자주 하는 실수와 해결법',
      mistakes: [
        {
          mistake_title: 'return을 빼먹음',
          wrong_code: 'def add(a, b): a + b',
          right_code: 'def add(a, b): return a + b',
          why_it_matters: '결과가 None이 된다',
          how_to_fix: 'return을 붙인다',
        },
      ],
    },
    ...overrides,
  }
}

export function makeDocument(overrides: Partial<LearningDocument> = {}): LearningDocument {
  return {
    id: 'd-1',
    taskId: 't-1',
    status: 'completed',
    content: makeContent(),
    failedChapters: [],
    generationError: null,
    generationStartedAt: '2026-11-18T01:00:00Z',
    generationCompletedAt: '2026-11-18T01:00:28Z',
    files: [makeFile()],
    ...overrides,
  }
}

// 서버(snake_case) 응답 형태.
export function serverDocument(overrides: Record<string, unknown> = {}) {
  return {
    id: 'd-1',
    task_id: 't-1',
    status: 'completed',
    content: makeContent(),
    failed_chapters: [],
    generation_error: null,
    generation_started_at: '2026-11-18T01:00:00Z',
    generation_completed_at: '2026-11-18T01:00:28Z',
    files: [makeFile()],
    ...overrides,
  }
}

export function serverStatus(overrides: Record<string, unknown> = {}) {
  return {
    task_id: 't-1',
    status: 'in_progress',
    generation_started_at: '2026-11-18T01:00:00Z',
    generation_completed_at: null,
    generation_error: null,
    failed_chapters: [],
    estimated_remaining_seconds: 40,
    ...overrides,
  }
}

export function makeStatus(overrides: Partial<DocumentStatusInfo> = {}): DocumentStatusInfo {
  return {
    taskId: 't-1',
    status: 'in_progress',
    generationStartedAt: '2026-11-18T01:00:00Z',
    generationCompletedAt: null,
    generationError: null,
    failedChapters: [],
    estimatedRemainingSeconds: 40,
    ...overrides,
  }
}

// 서버(apiClient.get)를 주소별로 흉내 낸다. Error를 돌려주면 그 오류로 거절한다.
export function mockDocumentApi(
  apiClient: { get: unknown },
  handlers: { document: () => unknown; status?: () => unknown },
) {
  return vi
    .spyOn(apiClient as { get: (url: string) => Promise<unknown> }, 'get')
    .mockImplementation((url: string) => {
      const body = url.endsWith('/document/status') ? handlers.status?.() : handlers.document()
      return body instanceof Error ? Promise.reject(body) : Promise.resolve({ data: body })
    })
}
