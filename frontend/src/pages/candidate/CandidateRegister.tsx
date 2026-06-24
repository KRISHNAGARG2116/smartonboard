import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import { GoogleLogin } from '@react-oauth/google'
import SteepCard from '../../components/design-system/SteepCard'
import SteepInput from '../../components/design-system/SteepInput'
import SteepButton from '../../components/design-system/SteepButton'

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
        <SteepButton variant="ghost" size="sm" to="/candidate/login">
          Sign in
        </SteepButton>
      </nav>

      {/* Centered form container */}
      <div style={{ maxWidth: '400px', margin: '0 auto', padding: 'var(--spacing-80) var(--spacing-24) var(--spacing-40)' }}>
        <h1 className="font-signifier" style={{ fontSize: 'var(--text-heading-sm)', color: 'var(--color-ink)', textAlign: 'left' }}>
          Create Candidate Profile
        </h1>
        <p style={{ fontSize: 'var(--text-caption)', color: 'var(--color-ash)', margin: 'var(--spacing-8) 0 var(--spacing-28)', textAlign: 'left' }}>
          Join the verified hiring ecosystem and showcase your matching skills.
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
              id="fullName"
              required
              value={fullName}
              onChange={e => setFullName(e.target.value)}
              placeholder="Jane Doe"
              label="Your Name"
            />

            <SteepInput
              id="email"
              type="email"
              required
              value={email}
              onChange={e => setEmail(e.target.value)}
              placeholder="you@domain.com"
              label="Email Address"
            />

            <SteepInput
              id="phoneNumber"
              type="tel"
              required
              value={phoneNumber}
              onChange={e => setPhoneNumber(e.target.value)}
              placeholder="+15551234567"
              label="Phone Number"
            />

            <SteepInput
              id="password"
              type="password"
              required
              minLength={8}
              value={password}
              onChange={e => setPassword(e.target.value)}
              placeholder="••••••••"
              label="Password"
              hint="Minimum 8 characters"
            />

            <SteepButton
              type="submit"
              disabled={submitting}
              variant="primary"
              block
              style={{ padding: '12px 20px', marginTop: 'var(--spacing-16)' }}
            >
              {submitting ? 'Creating profile…' : 'Create Profile'}
            </SteepButton>

            {/* Divider */}
            <div style={{ display: 'flex', alignItems: 'center', margin: 'var(--spacing-20) 0', color: 'var(--color-ash)', fontSize: 'var(--text-caption)' }}>
              <div style={{ flex: 1, height: '1px', background: 'var(--border)' }}></div>
              <span style={{ padding: '0 var(--spacing-12)' }}>or</span>
              <div style={{ flex: 1, height: '1px', background: 'var(--border)' }}></div>
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
          </SteepCard>
        </form>

        {/* Footer link */}
        <p style={{ marginTop: 'var(--spacing-20)', fontSize: 'var(--text-caption)', color: 'var(--color-ash)' }}>
          Already have a profile?{' '}
          <Link
            to="/candidate/login"
            style={{ color: 'var(--color-rust)', textDecoration: 'underline', textUnderlineOffset: 3 }}
          >
            Sign in
          </Link>
        </p>
      </div>
    </div>
  )
}
