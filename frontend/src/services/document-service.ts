import { useQuery } from '@tanstack/react-query'
import { useEffect } from 'react'
import type {
  DocumentContent,
  DocumentFile,
  DocumentStatus,
  DocumentStatusInfo,
  LearningDocument,
} from '@/types/document'
import { ApiError, apiClient } from './api-client'

export const POLL_INTERVAL_MS = 3000

const HTTP_NOT_FOUND = 404

interface DocumentDto {
  id: string
  task_id: string
  status: DocumentStatus
  content: DocumentContent
  failed_chapters: string[]
  generation_error: string | null
  generation_started_at: string | null
  generation_completed_at: string | null
  files: DocumentFile[]
}

interface DocumentStatusDto {
  task_id: string
  status: DocumentStatus
  generation_started_at: string | null
  generation_completed_at: string | null
  generation_error: string | null
  failed_chapters: string[]
  estimated_remaining_seconds: number | null
}

function toDocument(dto: DocumentDto): LearningDocument {
  return {
    id: dto.id,
    taskId: dto.task_id,
    status: dto.status,
    // 챕터 내용은 AI가 만든 JSON이라 키를 바꾸지 않는다(file_breakdown 키는 파일 경로).
    content: dto.content,
    failedChapters: dto.failed_chapters,
    generationError: dto.generation_error,
    generationStartedAt: dto.generation_started_at,
    generationCompletedAt: dto.generation_completed_at,
    files: dto.files,
  }
}

function toStatus(dto: DocumentStatusDto): DocumentStatusInfo {
  return {
    taskId: dto.task_id,
    status: dto.status,
    generationStartedAt: dto.generation_started_at,
    generationCompletedAt: dto.generation_completed_at,
    generationError: dto.generation_error,
    failedChapters: dto.failed_chapters,
    estimatedRemainingSeconds: dto.estimated_remaining_seconds,
  }
}

// 문서 행이 아직 없으면 서버가 404를 주므로 null("아직 문서가 없음")로 바꾼다.
export async function getDocument(taskId: string): Promise<LearningDocument | null> {
  try {
    const { data } = await apiClient.get<DocumentDto>(`/tasks/${taskId}/document`)
    return toDocument(data)
  } catch (error) {
    if (error instanceof ApiError && error.status === HTTP_NOT_FOUND) return null
    throw error
  }
}

export async function getDocumentStatus(taskId: string): Promise<DocumentStatusInfo> {
  const { data } = await apiClient.get<DocumentStatusDto>(`/tasks/${taskId}/document/status`)
  return toStatus(data)
}

function isGenerating(status: DocumentStatus | undefined): boolean {
  return status === 'pending' || status === 'in_progress'
}

// 문서를 조회하고, 생성 중이면 상태를 3초마다 확인한다. 끝나면(completed/failed) 문서를 다시 조회한다.
export function useDocument(taskId: string) {
  const documentQuery = useQuery({
    queryKey: ['tasks', taskId, 'document'],
    queryFn: () => getDocument(taskId),
  })
  const generating = isGenerating(documentQuery.data?.status)

  const statusQuery = useQuery({
    queryKey: ['tasks', taskId, 'document', 'status'],
    queryFn: () => getDocumentStatus(taskId),
    enabled: generating,
    refetchInterval: (query) =>
      query.state.data === undefined || isGenerating(query.state.data.status)
        ? POLL_INTERVAL_MS
        : false,
  })

  const latestStatus = statusQuery.data?.status
  const { refetch } = documentQuery
  useEffect(() => {
    if (generating && latestStatus !== undefined && !isGenerating(latestStatus)) void refetch()
  }, [generating, latestStatus, refetch])

  return {
    document: documentQuery.data,
    status: generating
      ? (latestStatus ?? documentQuery.data?.status ?? null)
      : (documentQuery.data?.status ?? null),
    estimatedRemainingSeconds: generating
      ? (statusQuery.data?.estimatedRemainingSeconds ?? null)
      : null,
    isPending: documentQuery.isPending,
    isError: documentQuery.isError,
    error: documentQuery.error,
    refetch,
  }
}
