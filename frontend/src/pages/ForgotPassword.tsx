import React, { useState } from 'react'
import { Link } from 'react-router-dom'
import axios from 'axios'

export default function ForgotPassword() {
  const [email, setEmail] = useState('')
  const [submitted, setSubmitted] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      // POST to forgot-password endpoint
      await axios.post('/api/v1/auth/forgot-password', { email })
      setSubmitted(true)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to request password reset link. Please try again.')
    } finally {
      setLoading(false)
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
        <Link to="/login" style={{ fontSize: 14, fontWeight: 400, color: 'var(--text)', textDecoration: 'none' }}>
          Sign In
        </Link>
      </nav>

      {/* Centered form container */}
      <div style={{ maxWidth: 400, margin: '0 auto', padding: '120px 24px 48px' }}>
        <h1 style={{ fontSize: 29, fontWeight: 500, lineHeight: 1.09, color: 'var(--text)', margin: 0, textAlign: 'left' }}>
          Forgot Password
        </h1>
        <p style={{ fontSize: 14, lineHeight: 1.33, color: 'var(--text-secondary)', margin: '8px 0 28px', textAlign: 'left' }}>
          Enter your email address to receive a secure recovery link.
        </p>

        {submitted ? (
          <div style={{
            border: '1px solid var(--border)',
            borderRadius: 12,
            padding: 24,
            textAlign: 'center',
            background: 'transparent'
          }}>
            <p style={{ fontSize: 15, lineHeight: 1.5, color: 'var(--text)', marginBottom: 20 }}>
              If your email is registered in our ecosystem, we have sent a secure password reset link to your inbox.
            </p>
            <Link to="/login" className="btn btn--primary" style={{
              display: 'inline-block',
              padding: '12px 24px',
              backgroundColor: 'var(--color-dark-cork)',
              color: 'var(--color-warm-cream)',
              textDecoration: 'none',
              borderRadius: 'var(--radius-buttons)',
              fontSize: 14,
              fontWeight: 500
            }}>
              Return to Sign In
            </Link>
          </div>
        ) : (
          <>
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
              <div style={{ marginBottom: 24 }}>
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
                  placeholder="yourname@domain.com"
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
                disabled={loading}
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
                  cursor: loading ? 'not-allowed' : 'pointer',
                  opacity: loading ? 0.6 : 1,
                  transition: 'opacity 0.15s ease',
                }}
              >
                {loading ? 'Sending link…' : 'Send Recovery Link'}
              </button>
            </form>
          </>
        )}
      </div>
    </div>
  )
}
