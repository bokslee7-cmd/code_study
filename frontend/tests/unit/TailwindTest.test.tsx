import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import App from '../../src/App'
import TailwindTest from '../../src/components/dev/TailwindTest'

afterEach(() => {
  vi.restoreAllMocks()
})

describe('Tailwind 클래스 테스트 섹션', () => {
  const section = () => screen.getByRole('region', { name: 'Tailwind 클래스 테스트' })

  it('bg-blue-500, text-white, p-3, rounded-lg 클래스가 적용된 샘플 박스를 보여준다', () => {
    render(<TailwindTest />)

    const sample = within(section()).getByTestId('tailwind-sample')

    expect(sample).toHaveClass('bg-blue-500', 'text-white', 'p-3', 'rounded-lg')
  })

  it.each([
    ['bg-blue-500', '배경색'],
    ['text-white', '글자색'],
    ['p-3', '안쪽 여백'],
    ['rounded-lg', '모서리'],
  ])('%s 클래스가 적용하는 스타일을 텍스트로 설명한다', (className, keyword) => {
    render(<TailwindTest />)

    const item = within(section()).getByRole('listitem', { name: className })

    expect(item).toHaveTextContent(className)
    expect(item).toHaveTextContent(keyword)
  })
})

describe('shadcn/ui 버튼 테스트 섹션', () => {
  const section = () => screen.getByRole('region', { name: 'shadcn/ui 버튼 테스트' })

  it('default, outline, ghost 버튼 3개를 보여준다', () => {
    render(<TailwindTest />)

    const buttons = within(section()).getAllByRole('button')

    expect(buttons.map((button) => button.textContent)).toEqual(['default', 'outline', 'ghost'])
  })

  it.each(['default', 'outline', 'ghost'])(
    '%s 버튼을 누르면 variant 이름을 alert로 표시한다',
    async (variant) => {
      const alert = vi.spyOn(window, 'alert').mockImplementation(() => {})
      render(<TailwindTest />)

      await userEvent.click(within(section()).getByRole('button', { name: variant }))

      expect(alert).toHaveBeenCalledTimes(1)
      expect(alert).toHaveBeenCalledWith(variant)
    },
  )

  it('세 버튼은 서로 다른 variant 스타일이다', () => {
    render(<TailwindTest />)

    const classNames = within(section())
      .getAllByRole('button')
      .map((button) => button.className)

    expect(new Set(classNames).size).toBe(3)
  })
})

describe('반응형 디자인 테스트 섹션', () => {
  const section = () => screen.getByRole('region', { name: '반응형 디자인 테스트' })

  it('카드 3개를 그리드로 배치한다', () => {
    render(<TailwindTest />)

    const grid = within(section()).getByTestId('responsive-grid')

    expect(grid).toHaveClass('grid')
    expect(within(grid).getAllByTestId('responsive-card')).toHaveLength(3)
  })

  it('모바일 1열, md 이상 2열, lg 이상 3열 클래스를 가진다', () => {
    render(<TailwindTest />)

    expect(within(section()).getByTestId('responsive-grid')).toHaveClass(
      'grid-cols-1',
      'md:grid-cols-2',
      'lg:grid-cols-3',
    )
  })

  it('각 breakpoint의 열 수를 텍스트로 설명한다', () => {
    render(<TailwindTest />)

    expect(section()).toHaveTextContent('모바일(기본): 1열')
    expect(section()).toHaveTextContent('태블릿(md 이상): 2열')
    expect(section()).toHaveTextContent('데스크톱(lg 이상): 3열')
  })
})

describe('/dev-test 라우트', () => {
  it('세 섹션을 모두 보여준다', () => {
    render(
      <QueryClientProvider client={new QueryClient()}>
        <MemoryRouter initialEntries={['/dev-test']}>
          <App />
        </MemoryRouter>
      </QueryClientProvider>,
    )

    expect(screen.getByRole('region', { name: 'Tailwind 클래스 테스트' })).toBeInTheDocument()
    expect(screen.getByRole('region', { name: 'shadcn/ui 버튼 테스트' })).toBeInTheDocument()
    expect(screen.getByRole('region', { name: '반응형 디자인 테스트' })).toBeInTheDocument()
  })
})
