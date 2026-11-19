import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

describe('Button', () => {
  it('버튼 역할로 렌더링되고 클릭 이벤트를 전달한다', async () => {
    const onClick = vi.fn()
    render(<Button onClick={onClick}>로그인</Button>)

    await userEvent.click(screen.getByRole('button', { name: '로그인' }))

    expect(onClick).toHaveBeenCalledTimes(1)
  })

  it('disabled이면 클릭할 수 없다', async () => {
    const onClick = vi.fn()
    render(
      <Button disabled onClick={onClick}>
        로그인
      </Button>,
    )

    await userEvent.click(screen.getByRole('button', { name: '로그인' }))

    expect(screen.getByRole('button', { name: '로그인' })).toBeDisabled()
    expect(onClick).not.toHaveBeenCalled()
  })

  it('variant에 따라 서로 다른 클래스가 붙는다', () => {
    render(
      <>
        <Button>기본</Button>
        <Button variant="destructive">삭제</Button>
      </>,
    )

    expect(screen.getByRole('button', { name: '삭제' }).className).not.toBe(
      screen.getByRole('button', { name: '기본' }).className,
    )
  })

  it('className을 넘기면 기본 클래스에 합쳐진다', () => {
    render(<Button className="my-custom-class">저장</Button>)

    expect(screen.getByRole('button', { name: '저장' })).toHaveClass('my-custom-class')
  })

  it('asChild로 링크 요소를 버튼 스타일로 렌더링할 수 있다', () => {
    render(
      <Button asChild>
        <a href="/register">회원가입</a>
      </Button>,
    )

    expect(screen.getByRole('link', { name: '회원가입' })).toHaveAttribute('href', '/register')
  })
})

describe('Input과 Label', () => {
  it('Label을 누르면 연결된 Input에 입력할 수 있다', async () => {
    render(
      <>
        <Label htmlFor="email">이메일</Label>
        <Input id="email" type="email" />
      </>,
    )

    await userEvent.type(screen.getByLabelText('이메일'), 'learner@example.com')

    expect(screen.getByLabelText('이메일')).toHaveValue('learner@example.com')
  })

  it('Input에 type과 placeholder가 전달된다', () => {
    render(<Input type="password" placeholder="비밀번호" />)

    expect(screen.getByPlaceholderText('비밀번호')).toHaveAttribute('type', 'password')
  })
})

describe('Card', () => {
  it('제목과 본문을 보여준다', () => {
    render(
      <Card>
        <CardHeader>
          <CardTitle>회원가입</CardTitle>
        </CardHeader>
        <CardContent>내용</CardContent>
      </Card>,
    )

    expect(screen.getByText('회원가입')).toBeInTheDocument()
    expect(screen.getByText('내용')).toBeInTheDocument()
  })

  it('설명, 우측 액션, 푸터까지 모든 영역을 보여주고 className을 합친다', () => {
    render(
      <Card className="my-card">
        <CardHeader>
          <CardTitle>로그인</CardTitle>
          <CardDescription>계정 정보를 입력하세요</CardDescription>
          <CardAction>도움말</CardAction>
        </CardHeader>
        <CardContent>폼</CardContent>
        <CardFooter>하단 안내</CardFooter>
      </Card>,
    )

    expect(screen.getByText('계정 정보를 입력하세요')).toBeInTheDocument()
    expect(screen.getByText('도움말')).toBeInTheDocument()
    expect(screen.getByText('하단 안내')).toBeInTheDocument()
    expect(screen.getByText('로그인').closest('[data-slot="card"]')).toHaveClass('my-card')
  })
})
