import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import { api, setAuthToken } from '../../api'

export default function RecruiterVerifyEmail() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [code, setCode] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [resending, setResending] = useState(false)

  useEffect(() => {
    if (user?.email) {
      setEmail(user.email)
    }
  }, [user])

  const handleVerify = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setSuccess(null)
    setSubmitting(true)

    try {
      const res = await api.post('/v1/auth/verify-email', {
        email: email.trim(),
        code: code.trim(),
      })
      setSuccess('Verification successful! Redirecting...')
      setAuthToken(res.data.access_token)
      setTimeout(() => {
        window.location.href = '/recruiter/dashboard'
      }, 1000)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Invalid or expired verification code.')
    } finally {
      setSubmitting(false)
    }
  }

  const handleResend = async () => {
    setError(null)
    setSuccess(null)
    setResending(true)

    try {
      await api.post('/v1/auth/verify-email/resend', {
        email: email.trim(),
      })
      setSuccess('A new verification code has been sent to your email.')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to resend verification code.')
    } finally {
      setResending(false)
    }
  }

  const handleSignOut = () => {
    logout()
    navigate('/recruiter/login')
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
        <div style={{ fontSize: 18, fontWeight: 500, color: 'var(--text)', letterSpacing: '0.04em' }}>
          SmartOnboard
        </div>
        <button
          onClick={handleSignOut}
          style={{
            fontSize: 14,
            fontWeight: 400,
            color: 'var(--text)',
            background: 'transparent',
            border: 'none',
            cursor: 'pointer',
            padding: 0
          }}
        >
          Sign Out
        </button>
      </nav>

      {/* Centered form container */}
      <div style={{ maxWidth: 400, margin: '0 auto', padding: '120px 24px 48px' }}>
        <h1 style={{ fontSize: 29, fontWeight: 500, lineHeight: 1.09, color: 'var(--text)', margin: 0, textAlign: 'left' }}>
          Verify Your Email
        </h1>
        <p style={{ fontSize: 14, lineHeight: 1.33, color: 'var(--text-secondary)', margin: '8px 0 28px', textAlign: 'left' }}>
          Enter the 6-digit verification code sent to your registered company email.
        </p>

        {/* Status banner */}
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

        {success && (
          <div
            role="alert"
            style={{
              border: '1px solid var(--accent)',
              borderRadius: 12,
              padding: '12px 16px',
              marginBottom: 20,
              color: 'var(--text)',
              fontSize: 14,
              lineHeight: 1.33,
              background: 'transparent',
            }}
          >
            {success}
          </div>
        )}

        {/* Form */}
        <form
          onSubmit={handleVerify}
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
              Company Email
            </label>
            <input
              id="email"
              type="email"
              required
              disabled={!!user}
              value={email}
              onChange={e => setEmail(e.target.value)}
              placeholder="recruiter@company.com"
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
                opacity: user ? 0.6 : 1,
                cursor: user ? 'not-allowed' : 'text'
              }}
            />
          </div>

          <div style={{ marginBottom: 24 }}>
            <label
              htmlFor="code"
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
              Verification Code (OTP)
            </label>
            <input
              id="code"
              type="text"
              required
              maxLength={6}
              value={code}
              onChange={e => setCode(e.target.value.replace(/\D/g, ''))}
              placeholder="123456"
              style={{
                width: '100%',
                background: 'transparent',
                border: 'none',
                borderBottom: '1px solid var(--border)',
                borderRadius: 0,
                padding: '8px 0',
                fontSize: 20,
                color: 'var(--text)',
                fontFamily: "var(--font-mono)",
                letterSpacing: '0.25em',
                textAlign: 'center',
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
              marginBottom: 12,
            }}
          >
            {submitting ? 'Verifying…' : 'Verify Email'}
          </button>

          <button
            type="button"
            disabled={resending}
            onClick={handleResend}
            style={{
              width: '100%',
              padding: '10px 24px',
              background: 'transparent',
              color: 'var(--text)',
              border: '1px solid var(--border)',
              borderRadius: 'var(--radius-buttons)',
              fontSize: 13,
              fontWeight: 500,
              fontFamily: "var(--font-sans)",
              cursor: resending ? 'not-allowed' : 'pointer',
              opacity: resending ? 0.6 : 1,
              transition: 'all 0.15s ease',
            }}
          >
            {resending ? 'Sending code…' : 'Resend Code'}
          </button>
        </form>
      </div>
    </div>
  )
}
