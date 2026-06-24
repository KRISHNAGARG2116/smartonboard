import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import { GoogleLogin } from '@react-oauth/google'

export default function CandidateRegister() {
  const { registerCandidate, loginWithGoogle } = useAuth()
  const navigate = useNavigate()
  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [phoneNumber, setPhoneNumber] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      const res = await registerCandidate({ email, password, full_name: fullName, phone_number: phoneNumber })
      if (res && res.verification_required) {
        localStorage.setItem('smartonboard_verify_email', email)
        navigate('/candidate/verify', {
          state: {
            email: email,
            email_verified: false,
            phone_verified: false,
            phone_number: phoneNumber
          }
        })
      } else {
        navigate('/candidate/dashboard')
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

  const labelStyle: React.CSSProperties = {
    display: 'block',
    fontSize: 10,
    fontWeight: 500,
    color: 'var(--text-secondary)',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
    lineHeight: 1.2,
    marginBottom: 8,
  }

  const inputStyle: React.CSSProperties = {
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
        <Link to="/candidate/login" style={{ fontSize: 14, fontWeight: 400, color: 'var(--text)', textDecoration: 'none' }}>
          Sign in
        </Link>
      </nav>

      {/* Centered form container */}
      <div style={{ maxWidth: 400, margin: '0 auto', padding: '120px 24px 48px' }}>
        <h1 style={{ fontSize: 29, fontWeight: 500, lineHeight: 1.09, color: 'var(--text)', margin: 0, textAlign: 'left' }}>
          Create Candidate Profile
        </h1>
        <p style={{ fontSize: 14, lineHeight: 1.33, color: 'var(--text-secondary)', margin: '8px 0 28px', textAlign: 'left' }}>
          Join the verified hiring ecosystem and showcase your matching skills.
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
              Email Address
            </label>
            <input
              id="email"
              type="email"
              required
              value={email}
              onChange={e => setEmail(e.target.value)}
              placeholder="you@domain.com"
              style={inputStyle}
            />
          </div>

          <div style={{ marginBottom: 20 }}>
            <label htmlFor="phoneNumber" style={labelStyle}>
              Phone Number
            </label>
            <input
              id="phoneNumber"
              type="tel"
              required
              value={phoneNumber}
              onChange={e => setPhoneNumber(e.target.value)}
              placeholder="+15551234567"
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
            <p style={{ fontSize: 10, lineHeight: 1.2, color: 'var(--text-secondary)', margin: '6px 0 0' }}>
              Minimum 8 characters
            </p>
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
            {submitting ? 'Creating profile…' : 'Create Profile'}
          </button>

          {/* Divider */}
          <div style={{ display: 'flex', alignItems: 'center', margin: '20px 0', color: 'var(--text-secondary)', fontSize: 12 }}>
            <div style={{ flex: 1, height: 1, background: 'var(--border)' }}></div>
            <span style={{ padding: '0 10px' }}>or</span>
            <div style={{ flex: 1, height: 1, background: 'var(--border)' }}></div>
          </div>

          {/* Google OAuth Register Button */}
          <div style={{ display: 'flex', justifyContent: 'center', width: '100%' }}>
            <GoogleLogin
              onSuccess={async (credentialResponse) => {
                setError(null)
                setSubmitting(true)
                try {
                  if (credentialResponse.credential) {
                    const res = await loginWithGoogle(credentialResponse.credential, 'candidate')
                    if (res && res.verification_required) {
                      localStorage.setItem('smartonboard_verify_email', res.user?.email || '')
                      navigate('/candidate/verify', {
                        state: {
                          email: res.user?.email || '',
                          email_verified: true,
                          phone_verified: false
                        }
                      })
                    } else {
                      navigate('/candidate/dashboard')
                    }
                  } else {
                    setError('No credential returned from Google.')
                  }
                } catch (err: any) {
                  if (err.response?.status === 403 && err.response?.data?.detail?.verification_required) {
                    const detail = err.response.data.detail
                    localStorage.setItem('smartonboard_verify_email', detail.email)
                    navigate('/candidate/verify', {
                      state: {
                        email: detail.email,
                        email_verified: detail.email_verified,
                        phone_verified: detail.phone_verified,
                        phone_number: detail.phone_number
                      }
                    })
                  } else {
                    setError(err.response?.data?.detail || 'Google authentication failed.')
                  }
                } finally {
                  setSubmitting(false)
                }
              }}
              onError={() => {
                setError('Google Sign-In failed.')
              }}
              theme="outline"
              size="large"
              width="350"
            />
          </div>
        </form>

        {/* Footer link */}
        <p style={{ marginTop: 20, fontSize: 14, lineHeight: 1.33, color: 'var(--text-secondary)' }}>
          Already have a profile?{' '}
          <Link
            to="/candidate/login"
            style={{ color: 'var(--accent)', textDecoration: 'underline', textUnderlineOffset: 3 }}
          >
            Sign in
          </Link>
        </p>
      </div>
    </div>
  )
}
