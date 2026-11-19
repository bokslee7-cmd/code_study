import { useState } from 'react'
import {
  CHAPTER_KEYS,
  type ChapterContentMap,
  type ChapterKey,
  type DocumentContent,
  type GenerationFailedChapter,
  type LinePosition,
} from '@/types/document'
import Chapter1 from './chapters/Chapter1'
import Chapter2 from './chapters/Chapter2'
import Chapter4 from './chapters/Chapter4'
import GenericChapter from './chapters/GenericChapter'

const DEFAULT_TITLES: Record<ChapterKey, string> = {
  chapter1: '이 코드가 하는 일',
  chapter2: '알아야 할 기본 개념',
  chapter3: '코드 구조 한눈에 보기',
  chapter4: '코드 한 줄씩 완전 해부',
  chapter5: '실행 흐름 따라가기',
  chapter6: '핵심 개념 정리',
  chapter7: '자주 하는 실수와 해결법',
}

interface ExplanationPanelProps {
  content: DocumentContent
  failedChapters: string[]
  activeLine?: LinePosition | null
  scrollTarget?: LinePosition | null
  onLineSelect?: (position: LinePosition) => void
}

function isFailedChapter(chapter: DocumentContent[ChapterKey]): chapter is GenerationFailedChapter {
  return chapter !== undefined && 'generation_failed' in chapter
}

export default function ExplanationPanel({
  content,
  failedChapters,
  activeLine,
  scrollTarget,
  onLineSelect,
}: ExplanationPanelProps) {
  const [activeKey, setActiveKey] = useState<ChapterKey>('chapter1')

  const failed = (key: ChapterKey) => failedChapters.includes(key) || isFailedChapter(content[key])

  function renderChapter(key: ChapterKey) {
    const chapter = content[key]
    if (failed(key)) {
      return (
        <div className="flex flex-col gap-1">
          <p className="font-medium text-amber-700">생성 실패</p>
          <p className="text-sm">이 섹션을 만들지 못했습니다. 질문하기로 보충할 수 있어요.</p>
        </div>
      )
    }
    if (chapter === undefined) {
      return <p className="text-sm text-muted-foreground">이 챕터의 내용이 아직 없습니다.</p>
    }
    // 위에서 실패 챕터를 걸렀으므로 여기서는 CHAPTER_SCHEMA 형태다.
    const body = chapter as ChapterContentMap[typeof key]
    switch (key) {
      case 'chapter1':
        return <Chapter1 chapter={body as ChapterContentMap['chapter1']} />
      case 'chapter2':
        return <Chapter2 chapter={body as ChapterContentMap['chapter2']} />
      case 'chapter4':
        return (
          <Chapter4
            chapter={body as ChapterContentMap['chapter4']}
            activeLine={activeLine}
            scrollTarget={scrollTarget}
            onLineSelect={onLineSelect}
          />
        )
      case 'chapter3':
        return <GenericChapter chapterKey={key} chapter={body as ChapterContentMap['chapter3']} />
      case 'chapter5':
        return <GenericChapter chapterKey={key} chapter={body as ChapterContentMap['chapter5']} />
      case 'chapter6':
        return <GenericChapter chapterKey={key} chapter={body as ChapterContentMap['chapter6']} />
      case 'chapter7':
        return <GenericChapter chapterKey={key} chapter={body as ChapterContentMap['chapter7']} />
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <nav aria-label="챕터 이동" className="flex flex-wrap gap-1">
        {CHAPTER_KEYS.map((key, index) => {
          const chapter = content[key]
          const title =
            !failed(key) && chapter !== undefined && 'title' in chapter
              ? chapter.title
              : DEFAULT_TITLES[key]
          return (
            <button
              key={key}
              type="button"
              aria-current={key === activeKey ? 'step' : undefined}
              onClick={() => setActiveKey(key)}
              className="rounded-md border px-2 py-1 text-xs aria-[current=step]:bg-primary aria-[current=step]:text-primary-foreground"
            >
              {index + 1}. {title}
              {failed(key) && <span className="ml-1">(생성 실패)</span>}
            </button>
          )
        })}
      </nav>
      {renderChapter(activeKey)}
    </div>
  )
}
