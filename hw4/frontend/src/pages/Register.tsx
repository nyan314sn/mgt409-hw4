import { useState, type FormEvent } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import AuthLayout from '../components/AuthLayout.tsx'
import { useAuth } from '../lib/auth.ts'
import { ApiError } from '../lib/authApi.ts'
import { useTitle } from '../lib/useTitle.ts'

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

type Fields = { firstName: string; lastName: string; email: string; password: string; confirm: string }
type Errors = Partial<Record<keyof Fields, string>>

const LABELS: Record<keyof Fields, { label: string; type: string; autoComplete: string; hint?: string }> = {
  firstName: { label: 'First name', type: 'text', autoComplete: 'given-name' },
  lastName: { label: 'Last name', type: 'text', autoComplete: 'family-name' },
  email: { label: 'Email', type: 'email', autoComplete: 'email' },
  password: { label: 'Password', type: 'password', autoComplete: 'new-password', hint: 'At least 8 characters.' },
  confirm: { label: 'Confirm password', type: 'password', autoComplete: 'new-password' },
}

/** Backend field names -> form field names, for server-side validation messages. */
const SERVER_FIELDS: Record<string, keyof Fields> = {
  first_name: 'firstName', last_name: 'lastName', email: 'email', password: 'password',
}

function validate(f: Fields): Errors {
  const e: Errors = {}
  if (!f.firstName.trim()) e.firstName = 'Enter your first name.'
  if (!f.lastName.trim()) e.lastName = 'Enter your last name.'
  if (!EMAIL_RE.test(f.email.trim())) e.email = 'Enter a valid email address.'
  if (f.password.length < 8) e.password = 'Use at least 8 characters.'
  else if (f.password.length > 128) e.password = 'Use 128 characters or fewer.'
  if (f.confirm !== f.password) e.confirm = 'Passwords don’t match.'
  return e
}

export default function Register() {
  const { user, register } = useAuth()
  useTitle('Create account')
  const navigate = useNavigate()
  const location = useLocation()
  const from = (location.state as { from?: string } | null)?.from ?? '/'

  const [fields, setFields] = useState<Fields>({ firstName: '', lastName: '', email: '', password: '', confirm: '' })
  const [errors, setErrors] = useState<Errors>({})
  const [formError, setFormError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  if (user && !submitting) return <Navigate to={from} replace />

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    const next = validate(fields)
    setErrors(next)
    setFormError('')
    if (Object.keys(next).length) return

    setSubmitting(true)
    try {
      await register({
        first_name: fields.firstName.trim(),
        last_name: fields.lastName.trim(),
        email: fields.email.trim(),
        password: fields.password,
      })
      navigate(from, { replace: true })
    } catch (err) {
      if (err instanceof ApiError) {
        const fieldErrors: Errors = {}
        for (const [key, msg] of Object.entries(err.fields)) {
          if (SERVER_FIELDS[key]) fieldErrors[SERVER_FIELDS[key]] = msg
        }
        setErrors(fieldErrors)
        setFormError(err.message)
      } else {
        setFormError('Something went wrong. Please try again.')
      }
      setSubmitting(false)
    }
  }

  const field = (key: keyof Fields) => {
    const errId = `reg-${key}-err`
    const hintId = `reg-${key}-hint`
    const describedBy = [errors[key] && errId, LABELS[key].hint && hintId].filter(Boolean).join(' ') || undefined
    return (
      <label className="field" key={key}>
        <span>{LABELS[key].label}</span>
        <input
          type={LABELS[key].type}
          autoComplete={LABELS[key].autoComplete}
          value={fields[key]}
          onChange={(e) => setFields({ ...fields, [key]: e.target.value })}
          aria-invalid={!!errors[key]}
          aria-describedby={describedBy}
        />
        {LABELS[key].hint && !errors[key] && <small id={hintId} className="muted">{LABELS[key].hint}</small>}
        {errors[key] && <small id={errId} className="field__error">{errors[key]}</small>}
      </label>
    )
  }

  return (
    <AuthLayout
      eyebrow="Join the pack"
      title="Create account"
      aside={
        <>
          <h2>Why sign up?</h2>
          <ul className="perks">
            <li>Chat with our shop assistant about sizes, colors, and gifts</li>
            <li>Keep your conversation history between visits</li>
            <li>Be first to hear when your college’s crest drops</li>
          </ul>
        </>
      }
    >
      <form className="form" onSubmit={onSubmit} noValidate aria-busy={submitting}>
        {formError && <p className="status status--error" role="alert">{formError}</p>}
        <div className="form__row">
          {field('firstName')}
          {field('lastName')}
        </div>
        {field('email')}
        {field('password')}
        {field('confirm')}
        <button type="submit" className="btn btn--primary btn--block" disabled={submitting}>
          {submitting ? 'Creating account…' : 'Create account'}
        </button>
        <p className="muted">Already have an account? <Link to="/login" state={{ from }}>Log in</Link></p>
      </form>
    </AuthLayout>
  )
}
