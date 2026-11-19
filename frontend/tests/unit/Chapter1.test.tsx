import { render, screen } from '@testing-library/react'
import Chapter1 from '../../src/components/document/chapters/Chapter1'

describe('Chapter1', () => {
  it('제목과 한 문장 요약을 보여준다', () => {
    render(<Chapter1 chapter={{ title: '이 코드가 하는 일', summary: '두 수를 더해 줍니다.' }} />)

    expect(screen.getByRole('heading', { level: 3, name: '이 코드가 하는 일' })).toBeInTheDocument()
    expect(screen.getByText('두 수를 더해 줍니다.')).toBeInTheDocument()
  })
})
