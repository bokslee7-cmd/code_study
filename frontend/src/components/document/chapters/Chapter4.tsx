import { useEffect, useRef } from 'react'
import type { Chapter4Content, LineExplanation, LinePosition } from '@/types/document'

interface Chapter4Props {
  chapter: Chapter4Content
  activeLine?: LinePosition | null
  // 코드를 스크롤하다 보이는 줄. 이 줄에 가장 가까운 해설로 스크롤한다.
  scrollTarget?: LinePosition | null
  onLineSelect?: (position: LinePosition) => void
}

const OPTIONAL_FIELDS = [
  { key: 'analogy', label: '비유' },
  { key: 'alternatives', label: '다른 방법' },
  { key: 'important_notes', label: '주의할 점' },
] as const

// 해설의 file_path가 빈 문자열이면 한 파일짜리 문서이므로 어느 파일과도 맞는 것으로 본다.
function isSameFile(explanationPath: string, filePath: string): boolean {
  return explanationPath === '' || filePath === '' || explanationPath === filePath
}

function matchesLine(explanation: LineExplanation, position: LinePosition): boolean {
  return (
    explanation.line_number === position.line &&
    isSameFile(explanation.file_path, position.filePath)
  )
}

// 줄 번호 이하의 해설 중 가장 가까운 것. 없으면 그 파일의 첫 해설.
function findNearest(explanations: LineExplanation[], target: LinePosition): number {
  const candidates = explanations
    .map((explanation, index) => ({ explanation, index }))
    .filter(({ explanation }) => isSameFile(explanation.file_path, target.filePath))
  const before = candidates.filter(({ explanation }) => explanation.line_number <= target.line)
  const pool = before.length > 0 ? before : candidates.slice(0, 1)
  const pick = (before.length > 0 ? Math.max : Math.min)(
    ...pool.map(({ explanation }) => explanation.line_number),
  )
  return pool.find(({ explanation }) => explanation.line_number === pick)?.index ?? -1
}

export default function Chapter4({
  chapter,
  activeLine = null,
  scrollTarget = null,
  onLineSelect,
}: Chapter4Props) {
  const itemRefs = useRef<Array<HTMLElement | null>>([])

  useEffect(() => {
    if (!scrollTarget) return
    const index = findNearest(chapter.explanations, scrollTarget)
    itemRefs.current[index]?.scrollIntoView({ block: 'nearest' })
  }, [chapter.explanations, scrollTarget])

  return (
    <section className="flex flex-col gap-3">
      <h3 className="text-lg font-semibold">{chapter.title}</h3>
      {chapter.explanations.length === 0 && (
        <p className="text-sm text-muted-foreground">줄별 해설이 없습니다.</p>
      )}
      {chapter.explanations.map((explanation, index) => {
        const active = activeLine !== null && matchesLine(explanation, activeLine)
        return (
          <article
            key={`${explanation.file_path}:${explanation.line_number}`}
            ref={(element) => {
              itemRefs.current[index] = element
            }}
            aria-current={active ? 'true' : undefined}
            className="rounded-lg border p-3 aria-[current=true]:border-primary aria-[current=true]:bg-muted"
          >
            <div className="mb-2 flex items-center gap-2">
              <button
                type="button"
                onClick={() =>
                  onLineSelect?.({ filePath: explanation.file_path, line: explanation.line_number })
                }
                className="rounded-md border px-2 py-0.5 text-xs font-medium hover:bg-muted"
              >
                줄 {explanation.line_number}
              </button>
              {explanation.file_path !== '' && (
                <span className="text-xs text-muted-foreground">{explanation.file_path}</span>
              )}
            </div>
            <code className="mb-2 block rounded bg-muted px-2 py-1 font-mono text-sm whitespace-pre-wrap">
              {explanation.code}
            </code>
            <dl className="flex flex-col gap-2 text-sm">
              <div>
                <dt className="text-xs text-muted-foreground">하는 일</dt>
                <dd>{explanation.what_it_does}</dd>
              </div>
              <div>
                <dt className="text-xs text-muted-foreground">문법 풀이</dt>
                <dd>{explanation.syntax_breakdown}</dd>
              </div>
              {OPTIONAL_FIELDS.filter(({ key }) => explanation[key] !== '').map(
                ({ key, label }) => (
                  <div key={key}>
                    <dt className="text-xs text-muted-foreground">{label}</dt>
                    <dd>{explanation[key]}</dd>
                  </div>
                ),
              )}
            </dl>
          </article>
        )
      })}
    </section>
  )
}
