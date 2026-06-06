import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'

export default function RecruiterLogin() {
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
      navigate('/recruiter/dashboard')
    } catch {
      setError('Invalid recruiter email or password.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div style={{ minHeight: '100vh', background: '#100904', color: '#ffedd7', fontFamily: "'Plus Jakarta Sans', sans-serif" }}>
      {/* Minimal top nav */}
      <nav style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        height: 56,
        padding: '0 24px',
        borderBottom: '1px solid #40372e',
      }}>
        <Link to="/" style={{ fontSize: 18, fontWeight: 500, color: '#ffedd7', textDecoration: 'none', letterSpacing: '0.04em' }}>
          ORYZO
        </Link>
        <Link to="/recruiter/register" style={{ fontSize: 14, fontWeight: 400, color: '#ffedd7', textDecoration: 'none' }}>
          Create recruiter workspace
        </Link>
      </nav>

      {/* Centered form container */}
      <div style={{ maxWidth: 400, margin: '0 auto', padding: '120px 24px 48px' }}>
        <h1 style={{ fontSize: 29, fontWeight: 500, lineHeight: 1.09, color: '#ffedd7', margin: 0, textAlign: 'left' }}>
          Recruiter Sign In
        </h1>
        <p style={{ fontSize: 14, lineHeight: 1.33, color: '#6c5f51', margin: '8px 0 28px', textAlign: 'left' }}>
          Access your company recruitment pipeline and screening queue.
        </p>

        {/* Error banner */}
        {error && (
          <div
            role="alert"
            style={{
              border: '1px solid #dc5000',
              borderRadius: 12,
              padding: '12px 16px',
              marginBottom: 20,
              color: '#dc5000',
              fontSize: 14,
              lineHeight: 1.33,
              background: 'transparent',
            }}
          >
            {error}
          </div>
        )}

        {/* Form */}
        <form
          onSubmit={handleSubmit}
          style={{
            border: '1px solid #ffedd7',
            borderRadius: 12,
            padding: 24,
            background: 'transparent',
          }}
        >
          <div style={{ marginBottom: 20 }}>
            <label
              htmlFor="email"
              style={{
                display: 'block',
                fontSize: 10,
                fontWeight: 500,
                color: '#6c5f51',
                textTransform: 'uppercase',
                letterSpacing: '0.05em',
                lineHeight: 1.2,
                marginBottom: 8,
              }}
            >
              Company Email
            </label>
            <input
              id="email"
              type="email"
              required
              value={email}
              onChange={e => setEmail(e.target.value)}
              placeholder="recruiter@company.com"
              style={{
                width: '100%',
                background: 'transparent',
                border: 'none',
                borderBottom: '1px solid #ffedd7',
                borderRadius: 0,
                padding: '8px 0',
                fontSize: 15,
                color: '#ffedd7',
                fontFamily: "'Plus Jakarta Sans', sans-serif",
                outline: 'none',
                boxSizing: 'border-box',
              }}
            />
          </div>

          <div style={{ marginBottom: 24 }}>
            <label
              htmlFor="password"
              style={{
                display: 'block',
                fontSize: 10,
                fontWeight: 500,
                color: '#6c5f51',
                textTransform: 'uppercase',
                letterSpacing: '0.05em',
                lineHeight: 1.2,
                marginBottom: 8,
              }}
            >
              Password
            </label>
            <input
              id="password"
              type="password"
              required
              value={password}
              onChange={e => setPassword(e.target.value)}
              placeholder="••••••••"
              style={{
                width: '100%',
                background: 'transparent',
                border: 'none',
                borderBottom: '1px solid #ffedd7',
                borderRadius: 0,
                padding: '8px 0',
                fontSize: 15,
                color: '#ffedd7',
                fontFamily: "'Plus Jakarta Sans', sans-serif",
                outline: 'none',
                boxSizing: 'border-box',
              }}
            />
          </div>

          <button
            type="submit"
            disabled={submitting}
            style={{
              width: '100%',
              padding: '14px 24px',
              background: '#382416',
              color: '#ffedd7',
              border: 'none',
              borderRadius: 36,
              fontSize: 14,
              fontWeight: 500,
              fontFamily: "'Plus Jakarta Sans', sans-serif",
              cursor: submitting ? 'not-allowed' : 'pointer',
              opacity: submitting ? 0.6 : 1,
              transition: 'opacity 0.15s ease',
            }}
          >
            {submitting ? 'Accessing Cockpit…' : 'Access Cockpit'}
          </button>
        </form>

        {/* Footer link */}
        <p style={{ marginTop: 20, fontSize: 14, lineHeight: 1.33, color: '#6c5f51' }}>
          No workspace?{' '}
          <Link
            to="/recruiter/register"
            style={{ color: '#dc5000', textDecoration: 'underline', textUnderlineOffset: 3 }}
          >
            Create one
          </Link>
        </p>
      </div>
    </div>
  )
}
