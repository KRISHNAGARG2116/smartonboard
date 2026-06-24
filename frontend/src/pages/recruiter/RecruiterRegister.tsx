import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import { GoogleLogin } from '@react-oauth/google'
import SteepCard from '../../components/design-system/SteepCard'
import SteepInput from '../../components/design-system/SteepInput'
import SteepButton from '../../components/design-system/SteepButton'

export default function RecruiterRegister() {
  const { register, loginWithGoogle } = useAuth()
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

  return (
    <div className="app-shell" style={{ background: 'var(--color-fog)', minHeight: '100vh' }}>
      {/* Minimal top nav */}
      <nav style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        height: 'var(--header-h)',
        paddingInline: 'var(--spacing-24)',
        borderBottom: '1px solid var(--border)',
        background: 'var(--color-pure-white)',
      }}>
        <Link to="/" style={{ fontSize: 'var(--text-body-lg)', fontWeight: 500, color: 'var(--color-ink)', textDecoration: 'none' }}>
          SmartOnboard
        </Link>
        <SteepButton variant="ghost" size="sm" to="/recruiter/login">
          Sign In
        </SteepButton>
      </nav>

      {/* Centered form container */}
      <div style={{ maxWidth: '400px', margin: '0 auto', padding: 'var(--spacing-80) var(--spacing-24) var(--spacing-40)' }}>
        <h1 className="font-signifier" style={{ fontSize: 'var(--text-heading-sm)', color: 'var(--color-ink)', textAlign: 'left', margin: 0 }}>
          Create Recruiter Workspace
        </h1>
        <p style={{ fontSize: 'var(--text-caption)', color: 'var(--color-ash)', margin: 'var(--spacing-8) 0 var(--spacing-28)', textAlign: 'left' }}>
          Set up your organization workspace and verify domain parameters.
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
              id="company"
              required
              value={companyName}
              onChange={e => setCompanyName(e.target.value)}
              placeholder="Acme Corp"
              label="Company Name"
            />

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
              placeholder="you@company.com"
              label="Company Email"
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
              {submitting ? 'Creating workspace…' : 'Create Workspace'}
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
                      await loginWithGoogle(credentialResponse.credential, 'recruiter')
                      navigate('/recruiter/dashboard')
                    } else {
                      setError('No credential returned from Google.')
                    }
                  } catch (err: any) {
                    setError(err.response?.data?.detail || 'Google authentication failed.')
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
          Already have a workspace?{' '}
          <Link
            to="/recruiter/login"
            style={{ color: 'var(--color-rust)', textDecoration: 'underline', textUnderlineOffset: 3 }}
          >
            Sign in
          </Link>
        </p>
      </div>
    </div>
  )
}
