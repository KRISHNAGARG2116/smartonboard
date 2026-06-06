import { useState, useEffect } from 'react'
import { useAuth } from '../context/AuthContext'
import CandidateLayout from '../components/CandidateLayout'
import {
  fetchCandidateProfile,
  updateCandidateProfile,
  sendCandidateEmailOtp,
  verifyCandidateEmailOtp,
  sendCandidatePhoneOtp,
  verifyCandidatePhoneOtp
} from '../api'

export default function CandidateProfilePage() {
  const { user } = useAuth()
  const [loading, setLoading] = useState(true)
  const [profile, setProfile] = useState<{
    id: string
    full_name: string
    phone_number: string | null
    phone_verified: boolean
    email_verified: boolean
    location: string | null
  } | null>(null)

  const [fullName, setFullName] = useState('')
  const [email] = useState(user?.email || '')
  const [phone, setPhone] = useState('')
  const [location, setLocation] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [successMsg, setSuccessMsg] = useState<string | null>(null)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)

  // OTP Verification States
  const [showEmailModal, setShowEmailModal] = useState(false)
  const [emailCode, setEmailCode] = useState('')
  const [emailVerifying, setEmailVerifying] = useState(false)
  const [emailVerifyError, setEmailVerifyError] = useState<string | null>(null)

  const [showPhoneModal, setShowPhoneModal] = useState(false)
  const [phoneCode, setPhoneCode] = useState('')
  const [phoneVerifying, setPhoneVerifying] = useState(false)
  const [phoneVerifyError, setPhoneVerifyError] = useState<string | null>(null)

  const loadProfile = async () => {
    try {
      const data = await fetchCandidateProfile()
      if (data && data.profile) {
        setProfile(data.profile)
        setFullName(data.profile.full_name || user?.full_name || '')
        setPhone(data.profile.phone_number || '')
        setLocation(data.profile.location || '')
      }
    } catch (err: any) {
      setErrorMsg('Failed to load profile details.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadProfile()
  }, [])

  const profileCompletion =
    (fullName ? 25 : 0) +
    (location ? 25 : 0) +
    (profile?.email_verified ? 25 : 0) +
    (profile?.phone_verified ? 25 : 0)

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault()
    setSubmitting(true)
    setSuccessMsg(null)
    setErrorMsg(null)

    try {
      const data = await updateCandidateProfile({
        full_name: fullName,
        phone_number: phone,
        location: location
      })
      if (data && data.profile) {
        setProfile(data.profile)
        setSuccessMsg('Your profile has been saved successfully.')
      }
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || 'Failed to update profile.')
    } finally {
      setSubmitting(false)
    }
  }

  const handleSendEmailOtp = async () => {
    if (!email) return
    setErrorMsg(null)
    setSuccessMsg(null)
    try {
      await sendCandidateEmailOtp(email)
      setShowEmailModal(true)
      setEmailVerifyError(null)
      setEmailCode('')
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || 'Failed to send verification code.')
    }
  }

  const handleVerifyEmailOtp = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!email || !emailCode) return
    setEmailVerifying(true)
    setEmailVerifyError(null)
    try {
      await verifyCandidateEmailOtp(email, emailCode)
      setShowEmailModal(false)
      setSuccessMsg('Email verified successfully!')
      loadProfile()
    } catch (err: any) {
      setEmailVerifyError(err.response?.data?.detail || 'Invalid or expired code.')
    } finally {
      setEmailVerifying(false)
    }
  }

  const handleSendPhoneOtp = async () => {
    if (!phone) {
      setErrorMsg('Please enter and save a phone number first.')
      return
    }
    setErrorMsg(null)
    setSuccessMsg(null)
    try {
      await sendCandidatePhoneOtp(phone)
      setShowPhoneModal(true)
      setPhoneVerifyError(null)
      setPhoneCode('')
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || 'Failed to send verification code.')
    }
  }

  const handleVerifyPhoneOtp = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!phone || !phoneCode) return
    setPhoneVerifying(true)
    setPhoneVerifyError(null)
    try {
      await verifyCandidatePhoneOtp(phone, phoneCode)
      setShowPhoneModal(false)
      setSuccessMsg('Phone number verified successfully!')
      loadProfile()
    } catch (err: any) {
      setPhoneVerifyError(err.response?.data?.detail || 'Invalid or expired code.')
    } finally {
      setPhoneVerifying(false)
    }
  }

  if (loading) {
    return (
      <CandidateLayout>
        <div className="container" style={{ padding: 'var(--space-16) 0', textAlign: 'center' }}>
          <div className="spinner spinner--lg" style={{ margin: '0 auto' }} />
        </div>
      </CandidateLayout>
    )
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

                {errorMsg && (
                  <div className="banner banner--error" style={{ padding: 'var(--space-3) var(--space-4)', borderRadius: '8px', fontSize: 'var(--text-sm)', marginBottom: 'var(--space-2)' }}>
                    ❌ {errorMsg}
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
              <div className="card__body" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
                {/* Email verification row */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 'var(--text-sm)' }}>
                    <span style={{ fontWeight: 550 }}>Email Address</span>
                    {profile?.email_verified ? (
                      <span className="badge badge--hire">Verified</span>
                    ) : (
                      <span className="badge badge--reject">Unverified</span>
                    )}
                  </div>
                  {!profile?.email_verified && (
                    <button
                      type="button"
                      onClick={handleSendEmailOtp}
                      className="btn btn--secondary btn--sm"
                      style={{ fontSize: '11px', alignSelf: 'flex-start', padding: '4px 10px' }}
                    >
                      Verify Email
                    </button>
                  )}
                </div>

                <hr style={{ border: 'none', borderTop: '1px solid var(--border)', margin: 0 }} />

                {/* Phone verification row */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 'var(--text-sm)' }}>
                    <span style={{ fontWeight: 550 }}>Phone Number</span>
                    {profile?.phone_verified ? (
                      <span className="badge badge--hire">Verified</span>
                    ) : (
                      <span className="badge badge--reject">Unverified</span>
                    )}
                  </div>
                  {!profile?.phone_verified && (
                    <button
                      type="button"
                      onClick={handleSendPhoneOtp}
                      className="btn btn--secondary btn--sm"
                      style={{ fontSize: '11px', alignSelf: 'flex-start', padding: '4px 10px' }}
                      disabled={!phone}
                    >
                      Verify Phone
                    </button>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Email Verification Modal */}
      {showEmailModal && (
        <div style={{ position: 'fixed', inset: 0, zIndex: 300, display: 'grid', placeItems: 'center' }}>
          <div style={{ position: 'absolute', inset: 0, background: 'rgba(0,0,0,0.5)', backdropFilter: 'blur(4px)' }} onClick={() => setShowEmailModal(false)} />
          <div className="card" style={{ zIndex: 310, width: 'min(400px, 90vw)', overflow: 'hidden' }}>
            <div className="card__header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h3 style={{ fontSize: '16px', fontWeight: 700 }}>Verify Email</h3>
              <button type="button" onClick={() => setShowEmailModal(false)} style={{ fontSize: '18px', cursor: 'pointer' }}>✕</button>
            </div>
            <form onSubmit={handleVerifyEmailOtp} className="card__body" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
              {emailVerifyError && <div className="banner banner--error" style={{ fontSize: 'var(--text-xs)' }}>{emailVerifyError}</div>}
              <p style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)' }}>
                We've sent a 6-digit code to <strong>{email}</strong>. Please enter it below to verify your email.
              </p>
              <div className="form-group" style={{ margin: 0 }}>
                <label className="form-label" htmlFor="emailCode">Verification Code</label>
                <input
                  id="emailCode"
                  type="text"
                  required
                  placeholder="123456"
                  maxLength={6}
                  className="form-input"
                  value={emailCode}
                  onChange={e => setEmailCode(e.target.value.replace(/\D/g, ''))}
                  style={{ textAlign: 'center', letterSpacing: '0.5em', fontSize: 'var(--text-lg)', fontFamily: 'var(--font-mono)' }}
                />
              </div>
              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 'var(--space-2)' }}>
                <button type="button" className="btn btn--secondary" onClick={() => setShowEmailModal(false)}>Cancel</button>
                <button type="submit" className="btn btn--accent" disabled={emailVerifying}>
                  {emailVerifying ? 'Verifying...' : 'Verify'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Phone Verification Modal */}
      {showPhoneModal && (
        <div style={{ position: 'fixed', inset: 0, zIndex: 300, display: 'grid', placeItems: 'center' }}>
          <div style={{ position: 'absolute', inset: 0, background: 'rgba(0,0,0,0.5)', backdropFilter: 'blur(4px)' }} onClick={() => setShowPhoneModal(false)} />
          <div className="card" style={{ zIndex: 310, width: 'min(400px, 90vw)', overflow: 'hidden' }}>
            <div className="card__header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h3 style={{ fontSize: '16px', fontWeight: 700 }}>Verify Phone</h3>
              <button type="button" onClick={() => setShowPhoneModal(false)} style={{ fontSize: '18px', cursor: 'pointer' }}>✕</button>
            </div>
            <form onSubmit={handleVerifyPhoneOtp} className="card__body" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
              {phoneVerifyError && <div className="banner banner--error" style={{ fontSize: 'var(--text-xs)' }}>{phoneVerifyError}</div>}
              <p style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)' }}>
                We've sent a 6-digit SMS code to <strong>{phone}</strong>. Please enter it below to verify.
              </p>
              <div className="form-group" style={{ margin: 0 }}>
                <label className="form-label" htmlFor="phoneCode">Verification Code</label>
                <input
                  id="phoneCode"
                  type="text"
                  required
                  placeholder="123456"
                  maxLength={6}
                  className="form-input"
                  value={phoneCode}
                  onChange={e => setPhoneCode(e.target.value.replace(/\D/g, ''))}
                  style={{ textAlign: 'center', letterSpacing: '0.5em', fontSize: 'var(--text-lg)', fontFamily: 'var(--font-mono)' }}
                />
              </div>
              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 'var(--space-2)' }}>
                <button type="button" className="btn btn--secondary" onClick={() => setShowPhoneModal(false)}>Cancel</button>
                <button type="submit" className="btn btn--accent" disabled={phoneVerifying}>
                  {phoneVerifying ? 'Verifying...' : 'Verify'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </CandidateLayout>
  )
}
