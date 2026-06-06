import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function Login() {
  const { login, loginCandidate } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [isCandidate, setIsCandidate] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      if (isCandidate) {
        await loginCandidate(email, password)
        navigate('/candidate/dashboard')
      } else {
        await login(email, password)
        navigate('/dashboard')
      }
    } catch {
      setError('Invalid email or password.')
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
        <Link to="/register" style={{ fontSize: 14, fontWeight: 400, color: '#ffedd7', textDecoration: 'none' }}>
          Create account
        </Link>
      </nav>

      {/* Centered form container */}
      <div style={{ maxWidth: 400, margin: '0 auto', padding: '120px 24px 48px' }}>
        <h1 style={{ fontSize: 29, fontWeight: 500, lineHeight: 1.09, color: '#ffedd7', margin: 0, textAlign: 'left' }}>
          Sign in
        </h1>
        <p style={{ fontSize: 14, lineHeight: 1.33, color: '#6c5f51', margin: '8px 0 28px', textAlign: 'left' }}>
          {isCandidate ? 'Access your candidate command center.' : 'Access your company recruitment pipeline.'}
        </p>

        {/* Role toggle */}
        <div style={{ display: 'flex', gap: 8, marginBottom: 28 }}>
          <button
            type="button"
            onClick={() => { setIsCandidate(false); setError(null) }}
            style={{
              flex: 1,
              padding: '10px 20px',
              fontSize: 14,
              fontWeight: 500,
              fontFamily: "'Plus Jakarta Sans', sans-serif",
              cursor: 'pointer',
              border: !isCandidate ? '1px solid transparent' : '1px solid #ffedd7',
              background: !isCandidate ? '#382416' : 'transparent',
              color: '#ffedd7',
              borderRadius: !isCandidate ? 36 : 22.5,
              transition: 'all 0.15s ease',
            }}
          >
            Hiring Talent
          </button>
          <button
            type="button"
            onClick={() => { setIsCandidate(true); setError(null) }}
            style={{
              flex: 1,
              padding: '10px 20px',
              fontSize: 14,
              fontWeight: 500,
              fontFamily: "'Plus Jakarta Sans', sans-serif",
              cursor: 'pointer',
              border: isCandidate ? '1px solid transparent' : '1px solid #ffedd7',
              background: isCandidate ? '#382416' : 'transparent',
              color: '#ffedd7',
              borderRadius: isCandidate ? 36 : 22.5,
              transition: 'all 0.15s ease',
            }}
          >
            Looking for Job
          </button>
        </div>

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
              Email
            </label>
            <input
              id="email"
              type="email"
              required
              value={email}
              onChange={e => setEmail(e.target.value)}
              placeholder="you@company.com"
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
              minLength={8}
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
            {submitting ? 'Signing in…' : 'Sign in'}
          </button>
        </form>

        {/* Footer link */}
        <p style={{ marginTop: 20, fontSize: 14, lineHeight: 1.33, color: '#6c5f51' }}>
          No account?{' '}
          {isCandidate ? (
            <Link
              to="/register?role=candidate"
              style={{ color: '#dc5000', textDecoration: 'underline', textUnderlineOffset: 3 }}
            >
              Create one
            </Link>
          ) : (
            <Link
              to="/register"
              style={{ color: '#dc5000', textDecoration: 'underline', textUnderlineOffset: 3 }}
            >
              Create one
            </Link>
          )}
        </p>
      </div>
    </div>
  )
}
