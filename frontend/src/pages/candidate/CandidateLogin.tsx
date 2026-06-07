import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'

export default function CandidateLogin() {
  const { loginCandidate } = useAuth()
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
      await loginCandidate(email, password)
      navigate('/candidate/dashboard')
    } catch {
      setError('Invalid candidate email or password.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)', color: 'var(--text)', fontFamily: "var(--font-sans)" }}>
      {/* Minimal top nav */}
      <nav style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        height: 56,
        padding: '0 24px',
        borderBottom: '1px solid var(--border)',
      }}>
        <Link to="/" style={{ fontSize: 18, fontWeight: 500, color: 'var(--text)', textDecoration: 'none', letterSpacing: '0.04em' }}>
          SmartOnboard
        </Link>
        <Link to="/candidate/register" style={{ fontSize: 14, fontWeight: 400, color: 'var(--text)', textDecoration: 'none' }}>
          Create profile
        </Link>
      </nav>

      {/* Centered form container */}
      <div style={{ maxWidth: 400, margin: '0 auto', padding: '120px 24px 48px' }}>
        <h1 style={{ fontSize: 29, fontWeight: 500, lineHeight: 1.09, color: 'var(--text)', margin: 0, textAlign: 'left' }}>
          Candidate Sign In
        </h1>
        <p style={{ fontSize: 14, lineHeight: 1.33, color: 'var(--text-secondary)', margin: '8px 0 28px', textAlign: 'left' }}>
          Access your personal career matching hub and track applications.
        </p>

        {/* Error banner */}
        {error && (
          <div
            role="alert"
            style={{
              border: '1px solid var(--danger)',
              borderRadius: 12,
              padding: '12px 16px',
              marginBottom: 20,
              color: 'var(--danger)',
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
            border: '1px solid var(--border)',
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
                color: 'var(--text-secondary)',
                textTransform: 'uppercase',
                letterSpacing: '0.05em',
                lineHeight: 1.2,
                marginBottom: 8,
              }}
            >
              Email Address
            </label>
            <input
              id="email"
              type="email"
              required
              value={email}
              onChange={e => setEmail(e.target.value)}
              placeholder="you@domain.com"
              style={{
                width: '100%',
                background: 'transparent',
                border: 'none',
                borderBottom: '1px solid var(--border)',
                borderRadius: 0,
                padding: '8px 0',
                fontSize: 15,
                color: 'var(--text)',
                fontFamily: "var(--font-sans)",
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
                color: 'var(--text-secondary)',
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
                borderBottom: '1px solid var(--border)',
                borderRadius: 0,
                padding: '8px 0',
                fontSize: 15,
                color: 'var(--text)',
                fontFamily: "var(--font-sans)",
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
              background: 'var(--color-ink)',
              color: 'var(--color-pure-white)',
              border: 'none',
              borderRadius: 'var(--radius-buttons)',
              fontSize: 14,
              fontWeight: 500,
              fontFamily: "var(--font-sans)",
              cursor: submitting ? 'not-allowed' : 'pointer',
              opacity: submitting ? 0.6 : 1,
              transition: 'opacity 0.15s ease',
            }}
          >
            {submitting ? 'Signing in…' : 'Sign In'}
          </button>
        </form>

        {/* Footer link */}
        <p style={{ marginTop: 20, fontSize: 14, lineHeight: 1.33, color: 'var(--text-secondary)' }}>
          No profile?{' '}
          <Link
            to="/candidate/register"
            style={{ color: 'var(--accent)', textDecoration: 'underline', textUnderlineOffset: 3 }}
          >
            Create one
          </Link>
        </p>
      </div>
    </div>
  )
}
