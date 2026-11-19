import { Link } from 'react-router-dom'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { formatDate } from '@/lib/format-date'
import type { Project } from '@/services/project-service'
import ProjectProgress from './ProjectProgress'

interface ProjectCardProps {
  project: Project
}

// 카드 전체를 클릭 영역으로 만들되(after 가상 요소), 링크의 이름은 제목만 되도록 제목에만 링크를 건다.
export default function ProjectCard({ project }: ProjectCardProps) {
  return (
    <Card className="relative transition-shadow hover:ring-foreground/30">
      <CardHeader>
        <CardTitle>
          <Link
            to={`/projects/${project.id}`}
            className="outline-none after:absolute after:inset-0 after:content-[''] focus-visible:underline"
          >
            {project.title}
          </Link>
        </CardTitle>
        {project.description && (
          <p className="line-clamp-2 text-sm text-muted-foreground">{project.description}</p>
        )}
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        <ProjectProgress
          completedTaskCount={project.completedTaskCount}
          taskCount={project.taskCount}
          progressPercent={project.progressPercent}
        />
        <p className="text-xs text-muted-foreground">
          마지막 활동: {formatDate(project.lastActivityAt)}
        </p>
      </CardContent>
    </Card>
  )
}
