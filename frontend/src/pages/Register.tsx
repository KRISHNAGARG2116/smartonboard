import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import AppLayout from '../components/AppLayout'
import { useAuth } from '../context/AuthContext'

export default function Register() {
  const { register, registerCandidate } = useAuth()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const initialIsCandidate = searchParams.get('role') === 'candidate'
  
  const [companyName, setCompanyName] = useState('')
  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [isCandidate, setIsCandidate] = useState(initialIsCandidate)
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      if (isCandidate) {
        await registerCandidate({ email, password, full_name: fullName })
        navigate('/candidate/dashboard')
      } else {
        await register({ company_name: companyName, email, password, full_name: fullName })
        navigate('/dashboard')
      }
    } catch (err: unknown) {
      const msg =
        err && typeof err === 'object' && 'response' in err &&
        (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
      setError(typeof msg === 'string' ? msg : 'Registration failed. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <AppLayout>
      <div className="container" style={{ maxWidth: 480, padding: 'var(--space-16) var(--space-6)' }}>
        <h1 style={{ fontSize: 'var(--text-2xl)', fontWeight: 700, marginBottom: 'var(--space-2)' }}>
          Create account
        </h1>
        <p className="text-secondary" style={{ marginBottom: 'var(--space-6)' }}>
          {isCandidate ? 'Set up your candidate account on SmartOnboard.' : 'Set up your company on SmartOnboard.'}
        </p>

        <div style={{ display: 'flex', gap: 'var(--space-2)', marginBottom: 'var(--space-6)' }}>
          <button
            type="button"
            className={!isCandidate ? 'btn btn--primary' : 'btn btn--secondary'}
            style={{ flex: 1, fontSize: 'var(--text-sm)' }}
            onClick={() => {
              setIsCandidate(false)
              setError(null)
            }}
          >
            Hiring Talent
          </button>
          <button
            type="button"
            className={isCandidate ? 'btn btn--primary' : 'btn btn--secondary'}
            style={{ flex: 1, fontSize: 'var(--text-sm)' }}
            onClick={() => {
              setIsCandidate(true)
              setError(null)
            }}
          >
            Looking for Job
          </button>
        </div>

        {error && (
          <div className="banner banner--error" style={{ marginBottom: 'var(--space-5)' }} role="alert">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="card card__body">
          {!isCandidate && (
            <div className="form-group">
              <label className="form-label" htmlFor="company">Company name</label>
              <input
                id="company"
                required
                className="form-input"
                value={companyName}
                onChange={e => setCompanyName(e.target.value)}
              />
            </div>
          )}
          <div className="form-group">
            <label className="form-label" htmlFor="fullName">Your name</label>
            <input
              id="fullName"
              required
              className="form-input"
              value={fullName}
              onChange={e => setFullName(e.target.value)}
            />
          </div>
          <div className="form-group">
            <label className="form-label" htmlFor="email">Email</label>
            <input
              id="email"
              type="email"
              required
              className="form-input"
              value={email}
              onChange={e => setEmail(e.target.value)}
            />
          </div>
          <div className="form-group">
            <label className="form-label" htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              required
              minLength={8}
              className="form-input"
              value={password}
              onChange={e => setPassword(e.target.value)}
            />
            <p className="form-hint">Minimum 8 characters</p>
          </div>
          <button type="submit" className="btn btn--primary btn--block" disabled={submitting}>
            {submitting ? 'Creating account…' : 'Create account'}
          </button>
        </form>

        <p className="text-secondary" style={{ marginTop: 'var(--space-5)', fontSize: 'var(--text-sm)' }}>
          Already have an account? <Link to="/login" className="text-accent">Sign in</Link>
        </p>
      </div>
    </AppLayout>
  )
}
