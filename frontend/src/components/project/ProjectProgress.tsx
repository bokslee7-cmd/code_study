interface ProjectProgressProps {
  completedTaskCount: number
  taskCount: number
  progressPercent: number
}

// "완료/전체 태스크 완료", 퍼센트, 진행 막대를 함께 보여준다. 카드와 상세 화면이 공유한다.
export default function ProjectProgress({
  completedTaskCount,
  taskCount,
  progressPercent,
}: ProjectProgressProps) {
  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-center justify-between text-sm">
        <span>
          {completedTaskCount}/{taskCount} 태스크 완료
        </span>
        <span>{progressPercent}%</span>
      </div>
      <div
        role="progressbar"
        aria-label="진행률"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={progressPercent}
        className="h-2 overflow-hidden rounded-full bg-muted"
      >
        <div className="h-full bg-primary" style={{ width: `${progressPercent}%` }} />
      </div>
    </div>
  )
}
