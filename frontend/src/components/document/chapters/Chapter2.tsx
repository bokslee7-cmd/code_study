import type { Chapter2Content } from '@/types/document'

const FIELDS = [
  { key: 'explanation', label: '설명', code: false },
  { key: 'analogy', label: '비유', code: false },
  { key: 'example', label: '예시', code: true },
  { key: 'use_cases', label: '사용처', code: false },
] as const

export default function Chapter2({ chapter }: { chapter: Chapter2Content }) {
  return (
    <section className="flex flex-col gap-3">
      <h3 className="text-lg font-semibold">{chapter.title}</h3>
      {chapter.concepts.length === 0 && (
        <p className="text-sm text-muted-foreground">설명할 개념이 없습니다.</p>
      )}
      {chapter.concepts.map((concept) => (
        <article key={concept.name} className="rounded-lg border p-3">
          <h4 className="mb-2 font-medium">{concept.name}</h4>
          <dl className="flex flex-col gap-2 text-sm">
            {FIELDS.map(({ key, label, code }) => (
              <div key={key}>
                <dt className="text-xs text-muted-foreground">{label}</dt>
                <dd>
                  {code ? (
                    <code className="block rounded bg-muted px-2 py-1 font-mono whitespace-pre-wrap">
                      {concept[key]}
                    </code>
                  ) : (
                    concept[key]
                  )}
                </dd>
              </div>
            ))}
          </dl>
        </article>
      ))}
    </section>
  )
}
