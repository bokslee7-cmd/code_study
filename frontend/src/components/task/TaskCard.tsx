import { Link } from 'react-router-dom'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { formatDate } from '@/lib/format-date'
import type { Task } from '@/services/task-service'

interface TaskCardProps {
  task: Task
}

// ProjectCard와 같이 제목 링크를 카드 전체로 확장한다(after 가상 요소).
export default function TaskCard({ task }: TaskCardProps) {
  return (
    <Card className="relative transition-shadow hover:ring-foreground/30">
      <CardHeader>
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <span>Task {task.taskNumber}</span>
          {task.isCompleted && <span className="font-medium text-foreground">완료</span>}
        </div>
        <CardTitle>
          <Link
            to={`/projects/${task.projectId}/tasks/${task.id}`}
            className="outline-none after:absolute after:inset-0 after:content-[''] focus-visible:underline"
          >
            {task.title}
          </Link>
        </CardTitle>
        {task.description && (
          <p className="line-clamp-2 text-sm text-muted-foreground">{task.description}</p>
        )}
      </CardHeader>
      <CardContent>
        <p className="text-xs text-muted-foreground">생성일: {formatDate(task.createdAt)}</p>
      </CardContent>
    </Card>
  )
}
