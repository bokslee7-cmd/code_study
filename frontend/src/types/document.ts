// 학습 문서 타입. 챕터 내용 형태는 backend/src/services/ai/prompts.py 의 CHAPTER_SCHEMA를 옮긴 것이다.
// content 안쪽 키는 AI가 만든 JSON 그대로(snake_case)이고, file_breakdown의 키는 파일 경로라 변환하지 않는다.

export type DocumentStatus = 'pending' | 'in_progress' | 'completed' | 'failed'

export const CHAPTER_KEYS = [
  'chapter1',
  'chapter2',
  'chapter3',
  'chapter4',
  'chapter5',
  'chapter6',
  'chapter7',
] as const

export type ChapterKey = (typeof CHAPTER_KEYS)[number]

export interface GenerationFailedChapter {
  generation_failed: true
}

export interface Chapter1Content {
  title: string
  summary: string
}

export interface ConceptCard {
  name: string
  explanation: string
  analogy: string
  example: string
  use_cases: string
}

export interface Chapter2Content {
  title: string
  concepts: ConceptCard[]
}

export interface Chapter3Content {
  title: string
  flowchart: string
  file_breakdown: Record<string, string>
}

export interface LineExplanation {
  file_path: string
  line_number: number
  code: string
  what_it_does: string
  syntax_breakdown: string
  analogy: string
  alternatives: string
  important_notes: string
}

export interface Chapter4Content {
  title: string
  explanations: LineExplanation[]
}

export interface ExecutionStep {
  step_number: number
  action: string
  data_state: string
  explanation: string
}

export interface Chapter5Content {
  title: string
  steps: ExecutionStep[]
}

export interface KeyConcept {
  concept_name: string
  what_it_is: string
  why_used: string
  where_applied: string
}

export interface Chapter6Content {
  title: string
  concepts: KeyConcept[]
}

export interface CommonMistake {
  mistake_title: string
  wrong_code: string
  right_code: string
  why_it_matters: string
  how_to_fix: string
}

export interface Chapter7Content {
  title: string
  mistakes: CommonMistake[]
}

export interface ChapterContentMap {
  chapter1: Chapter1Content
  chapter2: Chapter2Content
  chapter3: Chapter3Content
  chapter4: Chapter4Content
  chapter5: Chapter5Content
  chapter6: Chapter6Content
  chapter7: Chapter7Content
}

// 생성 중인 문서는 챕터가 비어 있을 수 있어 모든 챕터를 선택값으로 둔다.
export type DocumentContent = {
  [K in ChapterKey]?: ChapterContentMap[K] | GenerationFailedChapter
}

export interface DocumentFile {
  path: string
  language: string
  content: string
}

export interface LearningDocument {
  id: string
  taskId: string
  status: DocumentStatus
  content: DocumentContent
  failedChapters: string[]
  generationError: string | null
  generationStartedAt: string | null
  generationCompletedAt: string | null
  files: DocumentFile[]
}

export interface DocumentStatusInfo {
  taskId: string
  status: DocumentStatus
  generationStartedAt: string | null
  generationCompletedAt: string | null
  generationError: string | null
  failedChapters: string[]
  estimatedRemainingSeconds: number | null
}

// 코드의 한 줄. filePath가 빈 문자열이면 첫 번째(유일한) 파일을 뜻한다.
export interface LinePosition {
  filePath: string
  line: number
}
