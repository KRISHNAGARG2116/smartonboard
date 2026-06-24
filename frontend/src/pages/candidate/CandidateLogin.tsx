import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import { GoogleLogin } from '@react-oauth/google'
import SteepCard from '../../components/design-system/SteepCard'
import SteepInput from '../../components/design-system/SteepInput'
import SteepButton from '../../components/design-system/SteepButton'

export default function CandidateLogin() {
  const { loginCandidate, loginWithGoogle } = useAuth()
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
      const res = await loginCandidate(email, password)
      if (res && res.verification_required) {
        localStorage.setItem('smartonboard_verify_email', email)
        navigate('/candidate/verify', {
          state: {
            email: email,
            email_verified: res.user?.email_verified || false,
            phone_verified: res.user?.phone_verified || false
          }
        })
      } else {
        const target = localStorage.getItem('smartonboard_redirect_target')
        if (target) {
          localStorage.removeItem('smartonboard_redirect_target')
          navigate(target)
        } else {
          navigate('/candidate/dashboard')
        }
      }
    } catch (err: any) {
      if (err.response?.status === 403 && err.response?.data?.detail?.verification_required) {
        const detail = err.response.data.detail
        localStorage.setItem('smartonboard_verify_email', detail.email || email)
        navigate('/candidate/verify', {
          state: {
            email: detail.email || email,
            email_verified: detail.email_verified,
            phone_verified: detail.phone_verified,
            phone_number: detail.phone_number
          }
        })
      } else {
        setError(err.response?.data?.detail || 'Invalid candidate email or password.')
      }
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="app-shell" style={{ background: 'var(--color-fog)' }}>
      {/* Minimal top nav */}
      <nav
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          height: 'var(--header-h)',
          paddingInline: 'var(--spacing-24)',
          borderBottom: '1px solid var(--border)',
          background: 'var(--color-pure-white)',
        }}
      >
        <Link to="/" style={{ fontSize: 'var(--text-body-lg)', fontWeight: 500, color: 'var(--color-ink)' }}>
          SmartOnboard
        </Link>
        <SteepButton variant="ghost" size="sm" to="/candidate/register">
          Create profile
        </SteepButton>
      </nav>

      {/* Centered form container */}
      <div style={{ maxWidth: '400px', margin: '0 auto', padding: 'var(--spacing-80) var(--spacing-24) var(--spacing-40)' }}>
        <h1 className="font-signifier" style={{ fontSize: 'var(--text-heading-sm)', color: 'var(--color-ink)', textAlign: 'left' }}>
          Candidate Sign In
        </h1>
        <p style={{ fontSize: 'var(--text-caption)', color: 'var(--color-ash)', margin: 'var(--spacing-8) 0 var(--spacing-28)', textAlign: 'left' }}>
          Access your personal career matching hub and track applications.
        </p>

        {/* Error banner */}
        {error && (
          <div className="banner banner--error" role="alert" style={{ marginBottom: 'var(--spacing-20)' }}>
            {error}
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit}>
          <SteepCard>
            <SteepInput
              id="email"
              type="email"
              required
              value={email}
              onChange={e => setEmail(e.target.value)}
              placeholder="you@domain.com"
              label="Email Address"
            />

            <div style={{ marginBottom: 'var(--spacing-16)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--spacing-8)' }}>
                <label htmlFor="password" className="form-label" style={{ marginBottom: 0 }}>
                  Password
                </label>
                <Link to="/forgot-password" style={{ fontSize: '11px', color: 'var(--color-ash)', textDecoration: 'underline' }}>
                  Forgot Password?
                </Link>
              </div>
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

            <SteepButton
              type="submit"
              disabled={submitting}
              variant="primary"
              block
              style={{ padding: '12px 20px', marginTop: 'var(--spacing-16)' }}
            >
              {submitting ? 'Signing in…' : 'Sign In'}
            </SteepButton>

            {/* Divider */}
            <div style={{ display: 'flex', alignItems: 'center', margin: 'var(--spacing-20) 0', color: 'var(--color-ash)', fontSize: 'var(--text-caption)' }}>
              <div style={{ flex: 1, height: '1px', background: 'var(--border)' }}></div>
              <span style={{ padding: '0 var(--spacing-12)' }}>or</span>
              <div style={{ flex: 1, height: '1px', background: 'var(--border)' }}></div>
            </div>

            {/* Google OAuth Login Button */}
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
                        const target = localStorage.getItem('smartonboard_redirect_target')
                        if (target) {
                          localStorage.removeItem('smartonboard_redirect_target')
                          navigate(target)
                        } else {
                          navigate('/candidate/dashboard')
                        }
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
          </SteepCard>
        </form>

        {/* Footer link */}
        <p style={{ marginTop: 'var(--spacing-20)', fontSize: 'var(--text-caption)', color: 'var(--color-ash)' }}>
          No profile?{' '}
          <Link
            to="/candidate/register"
            style={{ color: 'var(--color-rust)', textDecoration: 'underline', textUnderlineOffset: 3 }}
          >
            Create one
          </Link>
        </p>
      </div>
    </div>
  )
}
