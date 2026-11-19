import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import PasteCode from '../../src/components/upload/PasteCode'

describe('PasteCode', () => {
  it('코드 입력창과 언어 선택을 보여준다', () => {
    render(<PasteCode value={{ code: 'print(1)', language: 'python' }} onChange={vi.fn()} />)

    expect(screen.getByLabelText('코드')).toHaveValue('print(1)')
    expect(screen.getByLabelText('프로그래밍 언어')).toHaveValue('python')
  })

  it('언어를 아직 고르지 않았으면 안내 옵션이 선택되어 있다', () => {
    render(<PasteCode value={{ code: '', language: '' }} onChange={vi.fn()} />)

    expect(screen.getByRole('option', { name: '언어 선택' })).toHaveValue('')
    expect(screen.getByLabelText('프로그래밍 언어')).toHaveValue('')
  })

  it('지원 언어 8종을 고를 수 있다', () => {
    render(<PasteCode value={{ code: '', language: '' }} onChange={vi.fn()} />)

    const names = screen
      .getAllByRole('option')
      .slice(1)
      .map((option) => option.textContent)
    expect(names).toEqual(['Python', 'JavaScript', 'TypeScript', 'HTML', 'CSS', 'Java', 'C++', 'C'])
  })

  it('입력하면 onChange에 전체 값을 전달한다', async () => {
    const onChange = vi.fn()
    render(<PasteCode value={{ code: '', language: 'python' }} onChange={onChange} />)

    await userEvent.type(screen.getByLabelText('코드'), 'a')

    expect(onChange).toHaveBeenLastCalledWith({ code: 'a', language: 'python' })
  })

  it('언어를 바꾸면 onChange에 전달한다', async () => {
    const onChange = vi.fn()
    render(<PasteCode value={{ code: 'x', language: '' }} onChange={onChange} />)

    await userEvent.selectOptions(screen.getByLabelText('프로그래밍 언어'), 'cpp')

    expect(onChange).toHaveBeenCalledWith({ code: 'x', language: 'cpp' })
  })

  it('error가 있으면 alert로 보여준다', () => {
    render(
      <PasteCode
        value={{ code: '', language: '' }}
        onChange={vi.fn()}
        error="프로그래밍 언어를 선택하세요."
      />,
    )

    expect(screen.getByRole('alert')).toHaveTextContent('프로그래밍 언어를 선택하세요.')
  })

  it('disabled이면 입력을 막는다', () => {
    render(<PasteCode value={{ code: '', language: '' }} onChange={vi.fn()} disabled />)

    expect(screen.getByLabelText('코드')).toBeDisabled()
    expect(screen.getByLabelText('프로그래밍 언어')).toBeDisabled()
  })
})
