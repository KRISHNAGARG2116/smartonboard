import React, { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import axios from 'axios'

export default function ResetPassword() {
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token') || ''
  const email = searchParams.get('email') || ''

  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [completed, setCompleted] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    if (password !== confirmPassword) {
      setError('Passwords do not match.')
      return
    }

    if (password.length < 8) {
      setError('Password must be at least 8 characters long.')
      return
    }

    if (!token || !email) {
      setError('Invalid reset link. Missing email or token.')
      return
    }

    setLoading(true)
    try {
      // POST to reset-password endpoint
      await axios.post('/api/v1/auth/reset-password', {
        email,
        token,
        new_password: password
      })
      setCompleted(true)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to reset password. The link may have expired.')
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
          Reset Password
        </h1>
        <p style={{ fontSize: 14, lineHeight: 1.33, color: 'var(--text-secondary)', margin: '8px 0 28px', textAlign: 'left' }}>
          Enter and confirm your new password below.
        </p>

        {completed ? (
          <div style={{
            border: '1px solid var(--border)',
            borderRadius: 12,
            padding: 24,
            textAlign: 'center',
            background: 'transparent'
          }}>
            <p style={{ fontSize: 15, lineHeight: 1.5, color: 'var(--text)', marginBottom: 20 }}>
              Your password has been successfully reset.
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
              Go to Sign In
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
              className="card"
              style={{
                padding: 24,
              }}
            >
              <div className="form-group">
                <label htmlFor="password" className="form-label">
                  New Password
                </label>
                <input
                  id="password"
                  type="password"
                  required
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="form-input"
                />
              </div>

              <div className="form-group">
                <label htmlFor="confirm-password" className="form-label">
                  Confirm New Password
                </label>
                <input
                  id="confirm-password"
                  type="password"
                  required
                  value={confirmPassword}
                  onChange={e => setConfirmPassword(e.target.value)}
                  placeholder="••••••••"
                  className="form-input"
                />
              </div>

              <button
                type="submit"
                disabled={loading}
                className="btn btn--primary"
                style={{
                  width: '100%',
                  padding: '14px 24px',
                  cursor: loading ? 'not-allowed' : 'pointer',
                }}
              >
                {loading ? 'Resetting password…' : 'Reset Password'}
              </button>
            </form>
          </>
        )}
      </div>
    </div>
  )
}
