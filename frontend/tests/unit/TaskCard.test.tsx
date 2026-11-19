import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import TaskCard from '../../src/components/task/TaskCard'
import { makeTask } from '../fixtures/task'

function renderCard(task = makeTask()) {
  render(
    <MemoryRouter>
      <TaskCard task={task} />
    </MemoryRouter>,
  )
}

describe('TaskCard', () => {
  it('태스크 번호, 제목, 설명, 생성일을 보여준다', () => {
    renderCard()

    expect(screen.getByText('Task 1')).toBeInTheDocument()
    expect(screen.getByText('Add Todo Function')).toBeInTheDocument()
    expect(screen.getByText('할 일 추가 기능을 배운다')).toBeInTheDocument()
    expect(screen.getByText('생성일: 2026년 11월 2일')).toBeInTheDocument()
  })

  it('제목 링크가 태스크 상세로 이동한다', () => {
    renderCard()

    expect(screen.getByRole('link', { name: 'Add Todo Function' })).toHaveAttribute(
      'href',
      '/projects/p-1/tasks/t-1',
    )
  })

  it('설명이 없으면 설명 영역을 그리지 않는다', () => {
    renderCard(makeTask({ description: null }))

    expect(screen.queryByText('할 일 추가 기능을 배운다')).not.toBeInTheDocument()
  })

  it('완료한 태스크에는 "완료" 표시가 있다', () => {
    renderCard(makeTask({ isCompleted: true }))

    expect(screen.getByText('완료')).toBeInTheDocument()
  })

  it('완료하지 않은 태스크에는 "완료" 표시가 없다', () => {
    renderCard()

    expect(screen.queryByText('완료')).not.toBeInTheDocument()
  })
})
