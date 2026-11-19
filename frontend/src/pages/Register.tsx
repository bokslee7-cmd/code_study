import { Link, useNavigate } from 'react-router-dom'
import AuthCard from '@/components/auth/AuthCard'
import RegisterForm, { type RegisterValues } from '@/components/auth/RegisterForm'
import { register } from '../services/auth-service'

export default function Register() {
  const navigate = useNavigate()

  async function handleRegister(values: RegisterValues) {
    await register(values)
    navigate('/login', { replace: true, state: { registered: true } })
  }

  return (
    <AuthCard
      title="회원가입"
      footer={
        <p>
          이미 계정이 있으신가요?{' '}
          <Link to="/login" className="underline">
            로그인
          </Link>
        </p>
      }
    >
      <RegisterForm onSubmit={handleRegister} />
    </AuthCard>
  )
}
