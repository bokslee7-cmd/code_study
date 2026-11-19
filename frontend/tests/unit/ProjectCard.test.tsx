import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import ProjectCard from '../../src/components/project/ProjectCard'
import type { Project } from '../../src/services/project-service'
import { makeProject } from '../fixtures/project'

function renderCard(overrides: Partial<Project> = {}) {
  return render(
    <MemoryRouter>
      <ProjectCard project={makeProject(overrides)} />
    </MemoryRouter>,
  )
}

describe('ProjectCard', () => {
  it('제목과 설명을 보여주고, 제목은 프로젝트 상세로 가는 링크다', () => {
    renderCard()

    expect(screen.getByRole('link', { name: 'My Todo App' })).toHaveAttribute(
      'href',
      '/projects/p-1',
    )
    expect(screen.getByText('할 일 앱을 만들며 배우는 프로젝트')).toBeInTheDocument()
  })

  it('설명이 없으면 설명 자리에 아무것도 그리지 않는다', () => {
    renderCard({ description: null })

    expect(screen.queryByText('null')).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'My Todo App' })).toBeInTheDocument()
  })

  it('완료한 태스크 수를 "완료/전체 태스크 완료"로 보여준다', () => {
    renderCard({ taskCount: 5, completedTaskCount: 2, progressPercent: 40 })

    expect(screen.getByText('2/5 태스크 완료')).toBeInTheDocument()
  })

  it('태스크가 없으면 "0/0 태스크 완료"와 진행률 0%를 보여준다', () => {
    renderCard()

    expect(screen.getByText('0/0 태스크 완료')).toBeInTheDocument()
    expect(screen.getByRole('progressbar', { name: '진행률' })).toHaveAttribute(
      'aria-valuenow',
      '0',
    )
    expect(screen.getByText('0%')).toBeInTheDocument()
  })

  it('진행률을 퍼센트 글자와 진행 막대(aria-valuenow)로 보여준다', () => {
    renderCard({ taskCount: 5, completedTaskCount: 2, progressPercent: 40 })

    const bar = screen.getByRole('progressbar', { name: '진행률' })
    expect(bar).toHaveAttribute('aria-valuenow', '40')
    expect(bar).toHaveAttribute('aria-valuemin', '0')
    expect(bar).toHaveAttribute('aria-valuemax', '100')
    expect(screen.getByText('40%')).toBeInTheDocument()
  })

  it('마지막 활동일을 보여준다', () => {
    renderCard({ lastActivityAt: '2026-11-05T12:00:00Z' })

    expect(screen.getByText('마지막 활동: 2026년 11월 5일')).toBeInTheDocument()
  })
})
