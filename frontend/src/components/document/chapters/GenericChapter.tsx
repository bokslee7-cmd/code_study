import type {
  Chapter3Content,
  Chapter5Content,
  Chapter6Content,
  Chapter7Content,
} from '@/types/document'

// 3·5·6·7장은 전용 컴포넌트 없이 제목과 핵심 필드만 보여주는 최소한의 범용 렌더링을 쓴다.
export type GenericChapterProps =
  | { chapterKey: 'chapter3'; chapter: Chapter3Content }
  | { chapterKey: 'chapter5'; chapter: Chapter5Content }
  | { chapterKey: 'chapter6'; chapter: Chapter6Content }
  | { chapterKey: 'chapter7'; chapter: Chapter7Content }

function Field({ label, children }: { label: string; children: string }) {
  return (
    <div>
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="whitespace-pre-wrap">{children}</dd>
    </div>
  )
}

function Body(props: GenericChapterProps) {
  switch (props.chapterKey) {
    case 'chapter3':
      return (
        <>
          <pre className="overflow-x-auto rounded bg-muted p-2 font-mono text-sm">
            {props.chapter.flowchart}
          </pre>
          <dl className="flex flex-col gap-2 text-sm">
            {Object.entries(props.chapter.file_breakdown).map(([path, role]) => (
              <Field key={path} label={path}>
                {role}
              </Field>
            ))}
          </dl>
        </>
      )
    case 'chapter5':
      return props.chapter.steps.map((step) => (
        <article key={step.step_number} className="rounded-lg border p-3">
          <h4 className="mb-2 font-medium">단계 {step.step_number}</h4>
          <dl className="flex flex-col gap-2 text-sm">
            <Field label="일어나는 일">{step.action}</Field>
            <Field label="변수 값">{step.data_state}</Field>
            <Field label="설명">{step.explanation}</Field>
          </dl>
        </article>
      ))
    case 'chapter6':
      return props.chapter.concepts.map((concept) => (
        <article key={concept.concept_name} className="rounded-lg border p-3">
          <h4 className="mb-2 font-medium">{concept.concept_name}</h4>
          <dl className="flex flex-col gap-2 text-sm">
            <Field label="무엇인가요">{concept.what_it_is}</Field>
            <Field label="왜 쓰나요">{concept.why_used}</Field>
            <Field label="어디에 쓰였나요">{concept.where_applied}</Field>
          </dl>
        </article>
      ))
    case 'chapter7':
      return props.chapter.mistakes.map((mistake) => (
        <article key={mistake.mistake_title} className="rounded-lg border p-3">
          <h4 className="mb-2 font-medium">{mistake.mistake_title}</h4>
          <dl className="flex flex-col gap-2 text-sm">
            <Field label="틀린 코드">{mistake.wrong_code}</Field>
            <Field label="올바른 코드">{mistake.right_code}</Field>
            <Field label="왜 문제인가요">{mistake.why_it_matters}</Field>
            <Field label="고치는 방법">{mistake.how_to_fix}</Field>
          </dl>
        </article>
      ))
  }
}

export default function GenericChapter(props: GenericChapterProps) {
  return (
    <section className="flex flex-col gap-3">
      <h3 className="text-lg font-semibold">{props.chapter.title}</h3>
      <Body {...props} />
    </section>
  )
}
