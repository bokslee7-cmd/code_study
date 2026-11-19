import type { ReactNode } from 'react'
import { Card, CardContent, CardFooter, CardHeader } from '@/components/ui/card'

interface AuthCardProps {
  title: string
  notice?: string
  children: ReactNode
  footer: ReactNode
}

// 로그인/회원가입 페이지가 공유하는 화면 틀. h1 제목, (선택) 안내 문구, 폼, 하단 링크로 이뤄진다.
export default function AuthCard({ title, notice, children, footer }: AuthCardProps) {
  return (
    <main className="mx-auto flex min-h-screen w-full max-w-sm flex-col justify-center p-4">
      <Card>
        <CardHeader>
          <h1 className="text-lg font-semibold">{title}</h1>
          {notice && (
            <p role="status" className="text-sm text-muted-foreground">
              {notice}
            </p>
          )}
        </CardHeader>
        <CardContent>{children}</CardContent>
        <CardFooter className="text-sm">{footer}</CardFooter>
      </Card>
    </main>
  )
}
