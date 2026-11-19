import { useState, type FormEvent } from 'react'
import { Button } from '@/components/ui/button'
import { validateEmail, validateNewPassword } from '@/lib/auth-validation'
import FormField from './FormField'
import { useSubmitState } from './useSubmitState'

export interface RegisterValues {
  email: string
  password: string
}

interface RegisterFormProps {
  onSubmit: (values: RegisterValues) => Promise<void>
}

interface FieldErrors {
  email: string | null
  password: string | null
  confirm: string | null
}

const NO_ERRORS: FieldErrors = { email: null, password: null, confirm: null }

export default function RegisterForm({ onSubmit }: RegisterFormProps) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [errors, setErrors] = useState<FieldErrors>(NO_ERRORS)
  const { isPending, serverError, submit } = useSubmitState(onSubmit)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const nextErrors: FieldErrors = {
      email: validateEmail(email),
      password: validateNewPassword(password),
      confirm: confirm === password ? null : '비밀번호가 일치하지 않습니다.',
    }
    setErrors(nextErrors)
    if (nextErrors.email || nextErrors.password || nextErrors.confirm) return

    await submit({ email: email.trim(), password })
  }

  return (
    <form noValidate onSubmit={handleSubmit} className="flex flex-col gap-4">
      <FormField
        id="register-email"
        label="이메일"
        type="email"
        autoComplete="email"
        value={email}
        onChange={(event) => setEmail(event.target.value)}
        error={errors.email}
      />
      <FormField
        id="register-password"
        label="비밀번호"
        type="password"
        autoComplete="new-password"
        value={password}
        onChange={(event) => setPassword(event.target.value)}
        error={errors.password}
      />
      <FormField
        id="register-confirm"
        label="비밀번호 확인"
        type="password"
        autoComplete="new-password"
        value={confirm}
        onChange={(event) => setConfirm(event.target.value)}
        error={errors.confirm}
      />
      {serverError && (
        <p role="alert" className="text-sm text-destructive">
          {serverError}
        </p>
      )}
      <Button type="submit" disabled={isPending}>
        {isPending ? '가입 중...' : '회원가입'}
      </Button>
    </form>
  )
}
