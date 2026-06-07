import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'

export default function RecruiterRegister() {
  const { register } = useAuth()
  const navigate = useNavigate()
  const [companyName, setCompanyName] = useState('')
  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      await register({ company_name: companyName, email, password, full_name: fullName })
      navigate('/recruiter/dashboard')
    } catch (err: unknown) {
      const msg =
        err && typeof err === 'object' && 'response' in err &&
        (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
      setError(typeof msg === 'string' ? msg : 'Registration failed. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  const labelStyle: React.CSSProperties = {
    display: 'block',
    fontSize: 10,
    fontWeight: 500,
    color: '#6c5f51',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
    lineHeight: 1.2,
    marginBottom: 8,
  }

  const inputStyle: React.CSSProperties = {
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
          SmartOnboard
        </Link>
        <Link to="/recruiter/login" style={{ fontSize: 14, fontWeight: 400, color: '#ffedd7', textDecoration: 'none' }}>
          Sign in
        </Link>
      </nav>

      {/* Centered form container */}
      <div style={{ maxWidth: 400, margin: '0 auto', padding: '120px 24px 48px' }}>
        <h1 style={{ fontSize: 29, fontWeight: 500, lineHeight: 1.09, color: '#ffedd7', margin: 0, textAlign: 'left' }}>
          Create Recruiter Workspace
        </h1>
        <p style={{ fontSize: 14, lineHeight: 1.33, color: '#6c5f51', margin: '8px 0 28px', textAlign: 'left' }}>
          Set up your organization workspace and verify domain parameters.
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
            <label htmlFor="company" style={labelStyle}>
              Company name
            </label>
            <input
              id="company"
              required
              value={companyName}
              onChange={e => setCompanyName(e.target.value)}
              placeholder="Acme Corp"
              style={inputStyle}
            />
          </div>

          <div style={{ marginBottom: 20 }}>
            <label htmlFor="fullName" style={labelStyle}>
              Your name
            </label>
            <input
              id="fullName"
              required
              value={fullName}
              onChange={e => setFullName(e.target.value)}
              placeholder="Jane Doe"
              style={inputStyle}
            />
          </div>

          <div style={{ marginBottom: 20 }}>
            <label htmlFor="email" style={labelStyle}>
              Company Email
            </label>
            <input
              id="email"
              type="email"
              required
              value={email}
              onChange={e => setEmail(e.target.value)}
              placeholder="you@company.com"
              style={inputStyle}
            />
          </div>

          <div style={{ marginBottom: 24 }}>
            <label htmlFor="password" style={labelStyle}>
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
              style={inputStyle}
            />
            <p style={{ fontSize: 10, lineHeight: 1.2, color: '#6c5f51', margin: '6px 0 0' }}>
              Minimum 8 characters
            </p>
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
            {submitting ? 'Creating workspace…' : 'Create Workspace'}
          </button>
        </form>

        {/* Footer link */}
        <p style={{ marginTop: 20, fontSize: 14, lineHeight: 1.33, color: '#6c5f51' }}>
          Already have a workspace?{' '}
          <Link
            to="/recruiter/login"
            style={{ color: '#dc5000', textDecoration: 'underline', textUnderlineOffset: 3 }}
          >
            Sign in
          </Link>
        </p>
      </div>
    </div>
  )
}
