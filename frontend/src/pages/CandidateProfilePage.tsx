import { useState } from 'react'
import { useAuth } from '../context/AuthContext'
import CandidateLayout from '../components/CandidateLayout'

export default function CandidateProfilePage() {
  const { user } = useAuth()

  // Local state initialized with user info
  const [fullName, setFullName] = useState(user?.full_name || '')
  const [email] = useState(user?.email || '')
  const [phone, setPhone] = useState('')
  const [location, setLocation] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [successMsg, setSuccessMsg] = useState<string | null>(null)

  const profileCompletion = 65

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault()
    setSubmitting(true)
    setSuccessMsg(null)

    // Simulate saving profile details
    setTimeout(() => {
      setSubmitting(false)
      setSuccessMsg('Your profile has been saved successfully (changes will persist on backend in Phase D).')
    }, 800)
  }

  return (
    <CandidateLayout>
      <div className="container" style={{ padding: 'var(--space-6) 0 var(--space-12)' }}>
        <div className="dashboard-grid">
          {/* Main Form Column */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)' }}>
            <form onSubmit={handleSave} className="card">
              <div className="card__header">
                <h3 style={{ fontSize: 'var(--text-base)', fontWeight: 700 }}>Personal Information</h3>
                <p style={{ fontSize: 'var(--text-xs)', color: 'var(--text-secondary)', marginTop: '2px' }}>
                  Manage your public profile settings and contact credentials.
                </p>
              </div>

              <div className="card__body" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
                {successMsg && (
                  <div className="banner banner--success" style={{ padding: 'var(--space-3) var(--space-4)', borderRadius: '8px', fontSize: 'var(--text-sm)' }}>
                    ✅ {successMsg}
                  </div>
                )}

                <div className="form-group">
                  <label className="form-label" htmlFor="fullName">Full Name</label>
                  <input
                    id="fullName"
                    type="text"
                    required
                    className="form-input"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                  />
                </div>

                <div className="form-group">
                  <label className="form-label" htmlFor="email">Email Address</label>
                  <input
                    id="email"
                    type="email"
                    disabled
                    className="form-input"
                    value={email}
                    style={{ background: 'var(--bg-subtle)', cursor: 'not-allowed' }}
                  />
                  <p className="form-hint">Your email is managed by your sign-in settings.</p>
                </div>

                <div className="form-group">
                  <label className="form-label" htmlFor="phone">Phone Number</label>
                  <input
                    id="phone"
                    type="tel"
                    placeholder="+1 (555) 000-0000"
                    className="form-input"
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                  />
                  <p className="form-hint">Used for SMS OTP verification checks.</p>
                </div>

                <div className="form-group">
                  <label className="form-label" htmlFor="location">Location</label>
                  <input
                    id="location"
                    type="text"
                    placeholder="San Francisco, CA"
                    className="form-input"
                    value={location}
                    onChange={(e) => setLocation(e.target.value)}
                  />
                </div>

                <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 'var(--space-4)' }}>
                  <button type="submit" className="btn btn--accent" disabled={submitting}>
                    {submitting ? 'Saving changes…' : 'Save Profile'}
                  </button>
                </div>
              </div>
            </form>
          </div>

          {/* Right Sidebar Status Column */}
          <div className="dashboard-sidebar" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)' }}>
            {/* Status Summary */}
            <div className="card card__body" style={{ textAlign: 'center', padding: 'var(--space-6) var(--space-4)' }}>
              <div
                style={{
                  width: '72px',
                  height: '72px',
                  borderRadius: '50%',
                  background: 'linear-gradient(135deg, var(--accent) 0%, var(--accent-hover) 100%)',
                  margin: '0 auto var(--space-4)',
                  display: 'grid',
                  placeItems: 'center',
                  color: 'var(--text-inverse)',
                  fontSize: 'var(--text-xl)',
                  fontWeight: 800,
                  boxShadow: 'var(--shadow-md)'
                }}
              >
                {fullName.split(' ').map(n => n[0]).join('').slice(0,2).toUpperCase() || 'C'}
              </div>
              <h4 style={{ fontSize: 'var(--text-base)', fontWeight: 750 }}>{fullName || 'Candidate'}</h4>
              <p style={{ fontSize: 'var(--text-xs)', color: 'var(--text-secondary)', marginTop: '2px' }}>{email}</p>

              <div style={{ borderTop: '1px solid var(--border)', marginTop: 'var(--space-5)', paddingTop: 'var(--space-4)' }}>
                <div style={{ fontSize: 'var(--text-xs)', fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: 'var(--space-2)' }}>
                  Profile Completion
                </div>
                <div style={{ background: 'var(--border)', height: '8px', borderRadius: '4px', overflow: 'hidden', width: '100%' }}>
                  <div style={{ background: 'var(--accent)', height: '100%', width: `${profileCompletion}%` }} />
                </div>
                <div style={{ fontSize: '11px', fontWeight: 600, color: 'var(--text-secondary)', marginTop: 'var(--space-2)' }}>
                  {profileCompletion}% Complete
                </div>
              </div>
            </div>

            {/* Verification Badges */}
            <div className="card">
              <div className="card__header">
                <h3 style={{ fontSize: 'var(--text-sm)', fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                  Verification Status
                </h3>
              </div>
              <div className="card__body" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 'var(--text-sm)' }}>
                  <span>Email Verification</span>
                  <span className="badge badge--hire">Verified</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 'var(--text-sm)' }}>
                  <span>Phone Verification</span>
                  <span className="badge badge--interview">Unverified</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 'var(--text-sm)' }}>
                  <span>Security Trust Rating</span>
                  <span className="badge badge--neutral">Tier 1</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </CandidateLayout>
  )
}
