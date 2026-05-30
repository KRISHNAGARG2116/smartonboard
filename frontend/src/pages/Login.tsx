import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import AppLayout from '../components/AppLayout'
import { useAuth } from '../context/AuthContext'

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      await login(email, password)
      navigate('/dashboard')
    } catch {
      setError('Invalid email or password.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <AppLayout>
      <div className="container" style={{ maxWidth: 420, padding: 'var(--space-16) var(--space-6)' }}>
        <h1 style={{ fontSize: 'var(--text-2xl)', fontWeight: 700, marginBottom: 'var(--space-2)' }}>Sign in</h1>
        <p className="text-secondary" style={{ marginBottom: 'var(--space-8)' }}>
          Access your company recruitment pipeline.
        </p>

        {error && (
          <div className="banner banner--error" style={{ marginBottom: 'var(--space-5)' }} role="alert">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="card card__body">
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
          </div>
          <button type="submit" className="btn btn--primary btn--block" disabled={submitting}>
            {submitting ? 'Signing in…' : 'Sign in'}
          </button>
        </form>

        <p className="text-secondary" style={{ marginTop: 'var(--space-5)', fontSize: 'var(--text-sm)' }}>
          No account? <Link to="/register" className="text-accent">Create your company workspace</Link>
        </p>
      </div>
    </AppLayout>
  )
}
