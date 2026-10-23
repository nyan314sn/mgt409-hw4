import { useState, type FormEvent } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import AuthLayout from '../components/AuthLayout.tsx'
import { useAuth } from '../lib/auth.ts'
import { ApiError } from '../lib/authApi.ts'
import { useTitle } from '../lib/useTitle.ts'

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

export default function Login() {
  const { user, login } = useAuth()
  useTitle('Log in')
  const navigate = useNavigate()
  const location = useLocation()
  const from = (location.state as { from?: string } | null)?.from ?? '/'

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [errors, setErrors] = useState<{ email?: string; password?: string }>({})
  const [formError, setFormError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  if (user && !submitting) return <Navigate to={from} replace />

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    const next: typeof errors = {}
    if (!EMAIL_RE.test(email.trim())) next.email = 'Enter a valid email address.'
    if (!password) next.password = 'Enter your password.'
    setErrors(next)
    setFormError('')
    if (Object.keys(next).length) return

    setSubmitting(true)
    try {
      await login(email.trim(), password)
      navigate(from, { replace: true })
    } catch (err) {
      setPassword('')
      setFormError(err instanceof ApiError ? err.message : 'Something went wrong. Please try again.')
      setSubmitting(false)
    }
  }

  return (
    <AuthLayout
      eyebrow="Welcome back"
      title="Log in"
      aside={
        <>
          <h2>Your locker, saved.</h2>
          <p>Pick up where you left off: your conversations with our shop assistant, your sizes, and the pieces you were eyeing.</p>
        </>
      }
    >
      <form className="form" onSubmit={onSubmit} noValidate aria-busy={submitting}>
        {formError && <p className="status status--error" role="alert">{formError}</p>}
        <label className="field">
          <span>Email</span>
          <input type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)}
            aria-invalid={!!errors.email} aria-describedby={errors.email ? 'login-email-err' : undefined} />
          {errors.email && <small id="login-email-err" className="field__error">{errors.email}</small>}
        </label>
        <label className="field">
          <span>Password</span>
          <div className="field__inline">
            <input type={showPassword ? 'text' : 'password'} autoComplete="current-password" value={password}
              onChange={(e) => setPassword(e.target.value)}
              aria-invalid={!!errors.password} aria-describedby={errors.password ? 'login-pw-err' : undefined} />
            <button type="button" className="btn btn--ghost btn--sm" onClick={() => setShowPassword((s) => !s)}
              aria-pressed={showPassword}>
              {showPassword ? 'Hide' : 'Show'}
            </button>
          </div>
          {errors.password && <small id="login-pw-err" className="field__error">{errors.password}</small>}
        </label>
        <button type="submit" className="btn btn--primary btn--block" disabled={submitting}>
          {submitting ? 'Logging in…' : 'Log in'}
        </button>
        <p className="muted">New here? <Link to="/register" state={{ from }}>Create an account</Link></p>
      </form>
    </AuthLayout>
  )
}
