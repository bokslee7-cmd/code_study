import { Link, useLocation, useNavigate } from 'react-router-dom'
import AuthCard from '@/components/auth/AuthCard'
import LoginForm, { type LoginValues } from '@/components/auth/LoginForm'
import { login } from '../services/auth-service'
import { useAuthStore } from '../stores/auth-store'

const DEFAULT_REDIRECT = '/dashboard'
const REGISTERED_NOTICE = '회원가입이 완료되었습니다. 로그인해 주세요.'

interface LoginLocationState {
  registered?: boolean
  from?: { pathname: string; search?: string }
}

export default function Login() {
  const navigate = useNavigate()
  const state = useLocation().state as LoginLocationState | null
  const setSession = useAuthStore((store) => store.setSession)
  const redirectTo = state?.from
    ? `${state.from.pathname}${state.from.search ?? ''}`
    : DEFAULT_REDIRECT

  async function handleLogin(values: LoginValues) {
    const { accessToken, expiresIn, user } = await login(values)
    setSession({ accessToken, user, expiresIn })
    navigate(redirectTo, { replace: true })
  }

  return (
    <AuthCard
      title="로그인"
      notice={state?.registered ? REGISTERED_NOTICE : undefined}
      footer={
        <p>
          계정이 없으신가요?{' '}
          <Link to="/register" className="underline">
            회원가입
          </Link>
        </p>
      }
    >
      <LoginForm onSubmit={handleLogin} />
    </AuthCard>
  )
}
