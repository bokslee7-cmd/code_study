import { useState, type FormEvent } from 'react'
import { Button } from '@/components/ui/button'
import { validateEmail, validateRequiredPassword } from '@/lib/auth-validation'
import FormField from './FormField'
import { useSubmitState } from './useSubmitState'

export interface LoginValues {
  email: string
  password: string
}

interface LoginFormProps {
  onSubmit: (values: LoginValues) => Promise<void>
}

interface FieldErrors {
  email: string | null
  password: string | null
}

export default function LoginForm({ onSubmit }: LoginFormProps) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [errors, setErrors] = useState<FieldErrors>({ email: null, password: null })
  const { isPending, serverError, submit } = useSubmitState(onSubmit)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const nextErrors = {
      email: validateEmail(email),
      password: validateRequiredPassword(password),
    }
    setErrors(nextErrors)
    if (nextErrors.email || nextErrors.password) return

    await submit({ email: email.trim(), password })
  }

  return (
    <form noValidate onSubmit={handleSubmit} className="flex flex-col gap-4">
      <FormField
        id="login-email"
        label="이메일"
        type="email"
        autoComplete="email"
        value={email}
        onChange={(event) => setEmail(event.target.value)}
        error={errors.email}
      />
      <FormField
        id="login-password"
        label="비밀번호"
        type="password"
        autoComplete="current-password"
        value={password}
        onChange={(event) => setPassword(event.target.value)}
        error={errors.password}
      />
      {serverError && (
        <p role="alert" className="text-sm text-destructive">
          {serverError}
        </p>
      )}
      <Button type="submit" disabled={isPending}>
        {isPending ? '로그인 중...' : '로그인'}
      </Button>
    </form>
  )
}
