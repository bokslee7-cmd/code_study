import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

// Tailwind는 소스에 적힌 클래스 문자열을 읽어 CSS를 만든다. 클래스를 문자열 조합으로 만들면 누락되므로 전부 그대로 적는다.
const CLASS_DESCRIPTIONS = [
  { className: 'bg-blue-500', description: '배경색을 파란색(blue-500)으로 칠한다.' },
  { className: 'text-white', description: '글자색을 흰색으로 바꾼다.' },
  { className: 'p-3', description: '안쪽 여백을 사방 0.75rem(12px)으로 준다.' },
  {
    className: 'rounded-lg',
    description:
      '모서리를 둥글게 깎는다. 이 프로젝트 테마에서는 --radius 값(0.625rem, 약 10px)이다.',
  },
]

const BUTTON_VARIANTS = ['default', 'outline', 'ghost'] as const

const RESPONSIVE_CARDS = [
  { title: '카드 1', body: '화면 폭에 따라 열 수가 바뀐다.' },
  { title: '카드 2', body: '창 크기를 줄이거나 늘려 보자.' },
  { title: '카드 3', body: '1열 → 2열 → 3열 순서로 바뀐다.' },
]

function TailwindClassSection() {
  return (
    <section aria-label="Tailwind 클래스 테스트" className="space-y-3">
      <h2 className="text-lg font-semibold">Tailwind 클래스 테스트</h2>
      <div data-testid="tailwind-sample" className="bg-blue-500 text-white p-3 rounded-lg">
        bg-blue-500 text-white p-3 rounded-lg
      </div>
      <ul className="space-y-1 text-sm">
        {CLASS_DESCRIPTIONS.map(({ className, description }) => (
          <li key={className} aria-label={className}>
            <code className="font-mono font-semibold">{className}</code>: {description}
          </li>
        ))}
      </ul>
    </section>
  )
}

function ShadcnButtonSection() {
  return (
    <section aria-label="shadcn/ui 버튼 테스트" className="space-y-3">
      <h2 className="text-lg font-semibold">shadcn/ui 버튼 테스트</h2>
      <div className="flex gap-2">
        {BUTTON_VARIANTS.map((variant) => (
          <Button key={variant} variant={variant} onClick={() => window.alert(variant)}>
            {variant}
          </Button>
        ))}
      </div>
    </section>
  )
}

function ResponsiveGridSection() {
  return (
    <section aria-label="반응형 디자인 테스트" className="space-y-3">
      <h2 className="text-lg font-semibold">반응형 디자인 테스트</h2>
      <p className="text-sm">모바일(기본): 1열 / 태블릿(md 이상): 2열 / 데스크톱(lg 이상): 3열</p>
      <div
        data-testid="responsive-grid"
        className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3"
      >
        {RESPONSIVE_CARDS.map(({ title, body }) => (
          <Card key={title} data-testid="responsive-card">
            <CardHeader>
              <CardTitle>{title}</CardTitle>
            </CardHeader>
            <CardContent>{body}</CardContent>
          </Card>
        ))}
      </div>
    </section>
  )
}

// Tailwind CSS와 shadcn/ui가 화면에 제대로 적용되는지 눈으로 확인하는 개발용 영역.
export default function TailwindTest() {
  return (
    <div className="mt-8 space-y-8">
      <TailwindClassSection />
      <ShadcnButtonSection />
      <ResponsiveGridSection />
    </div>
  )
}
