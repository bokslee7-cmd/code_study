import { formatRemainingTime } from '@/lib/format-remaining-time'

interface GenerationProgressProps {
  status: 'pending' | 'in_progress'
  estimatedRemainingSeconds: number | null
}

const STATUS_LABEL = {
  pending: '문서 생성을 기다리는 중입니다',
  in_progress: '문서를 만드는 중입니다',
} as const

// 남은 비율을 알 수 없으므로 막대는 값 없이 "진행 중"만 알리는 형태로 둔다.
export default function GenerationProgress({
  status,
  estimatedRemainingSeconds,
}: GenerationProgressProps) {
  const remaining =
    estimatedRemainingSeconds !== null && estimatedRemainingSeconds > 0
      ? `예상 남은 시간: ${formatRemainingTime(estimatedRemainingSeconds)}`
      : formatRemainingTime(estimatedRemainingSeconds)

  return (
    <div className="flex flex-col gap-2 rounded-lg border p-4">
      <p className="font-medium">{STATUS_LABEL[status]}</p>
      <div
        role="progressbar"
        aria-label="문서 생성 진행 상황"
        className="h-2 w-full overflow-hidden rounded bg-muted"
      >
        <div className="h-full w-1/3 animate-pulse rounded bg-primary" />
      </div>
      <p className="text-sm text-muted-foreground">{remaining}</p>
    </div>
  )
}
