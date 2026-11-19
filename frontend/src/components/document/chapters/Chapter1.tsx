import type { Chapter1Content } from '@/types/document'

export default function Chapter1({ chapter }: { chapter: Chapter1Content }) {
  return (
    <section className="flex flex-col gap-2">
      <h3 className="text-lg font-semibold">{chapter.title}</h3>
      <p>{chapter.summary}</p>
    </section>
  )
}
