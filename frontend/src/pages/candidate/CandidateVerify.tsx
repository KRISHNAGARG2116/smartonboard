import { useState, useEffect } from 'react'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import {
  getVerificationStatus,
  sendPhoneOTP,
  verifyPhoneOTP,
  verifyEmailOTP
} from '../../api'

export default function CandidateVerify() {
  const navigate = useNavigate()
  const location = useLocation()
  const { user } = useAuth()

  // Primary State
  const [email, setEmail] = useState('')
  const [statusLoaded, setStatusLoaded] = useState(false)
  const [emailVerified, setEmailVerified] = useState(false)
  const [phoneVerified, setPhoneVerified] = useState(false)
  const [phoneNumber, setPhoneNumber] = useState('')

  // UI Flow States
  const [emailCode, setEmailCode] = useState('')
  const [phoneCode, setPhoneCode] = useState('')
  const [isEditingPhone, setIsEditingPhone] = useState(false)
  const [newPhone, setNewPhone] = useState('')

  // Feedback States
  const [errorEmail, setErrorEmail] = useState<string | null>(null)
  const [errorPhone, setErrorPhone] = useState<string | null>(null)
  const [successEmail, setSuccessEmail] = useState<string | null>(null)
  const [successPhone, setSuccessPhone] = useState<string | null>(null)
  const [submittingEmail, setSubmittingEmail] = useState(false)
  const [submittingPhone, setSubmittingPhone] = useState(false)
  const [sendingPhoneOTP, setSendingPhoneOTP] = useState(false)

  // Resend Cooldowns
  const [phoneCooldown, setPhoneCooldown] = useState(0)

  // Initialize Email
  useEffect(() => {
    // 1. Check React Router state
    let targetEmail = (location.state as any)?.email || ''

    // 2. Check query parameter
    if (!targetEmail) {
      const params = new URLSearchParams(location.search)
      targetEmail = params.get('email') || ''
    }

    // 3. Check localStorage
    if (!targetEmail) {
      targetEmail = localStorage.getItem('smartonboard_verify_email') || ''
    }

    // 4. Fallback to logged-in user context
    if (!targetEmail && user) {
      targetEmail = user.email
    }

    if (targetEmail) {
      setEmail(targetEmail)
      localStorage.setItem('smartonboard_verify_email', targetEmail)
      loadStatus(targetEmail)
    } else {
      setStatusLoaded(true)
    }
  }, [location, user])

  // Cooldown timer effect
  useEffect(() => {
    if (phoneCooldown > 0) {
      const timer = setTimeout(() => setPhoneCooldown(prev => prev - 1), 1000)
      return () => clearTimeout(timer)
    }
  }, [phoneCooldown])

  // Fetch verification status from backend
  const loadStatus = async (targetEmail: string) => {
    try {
      const data = await getVerificationStatus(targetEmail)
      setEmailVerified(data.email_verified)
      setPhoneVerified(data.phone_verified)
      setPhoneNumber(data.phone_number || '')
      setNewPhone(data.phone_number || '')

      // If both already verified, trigger redirect immediately
      if (data.email_verified && data.phone_verified) {
        handleRedirect()
      }
    } catch (err: any) {
      setErrorEmail(err.response?.data?.detail || 'Failed to fetch verification status.')
    } finally {
      setStatusLoaded(true)
    }
  }

  // Handle post-verification redirection
  const handleRedirect = () => {
    // 1. Check stored redirect target
    const target = localStorage.getItem('smartonboard_redirect_target')
    if (target) {
      localStorage.removeItem('smartonboard_redirect_target')
      window.location.href = target
    } else {
      // 2. Redirect based on role or context
      window.location.href = '/candidate/dashboard'
    }
  }

  // Handle Email Verification Check
  const handleVerifyEmail = async (e: React.FormEvent) => {
    e.preventDefault()
    setErrorEmail(null)
    setSuccessEmail(null)
    setSubmittingEmail(true)

    try {
      const res = await verifyEmailOTP(email, emailCode)
      setSuccessEmail('Email verified successfully!')
      setEmailVerified(true)

      // If this was the final verification step, the backend returns JWT, log in
      if (res && res.access_token) {
        // AuthContext interceptor will handle token if we just reload page or let it sync.
        // We set the token manually here so they are logged in immediately.
        localStorage.setItem('smartonboard_token', res.access_token)
        // If fully verified, redirect
        handleRedirect()
      } else {
        // Double check overall status
        loadStatus(email)
      }
    } catch (err: any) {
      setErrorEmail(err.response?.data?.detail || 'Failed to verify email code.')
    } finally {
      setSubmittingEmail(false)
    }
  }

  // Handle Phone OTP Request (for new or changed phone number)
  const handleSendPhoneOTP = async (e?: React.FormEvent) => {
    if (e) e.preventDefault()
    setErrorPhone(null)
    setSuccessPhone(null)
    setSendingPhoneOTP(true)

    const phoneToUse = (isEditingPhone || !phoneNumber) ? newPhone : phoneNumber
    if (!phoneToUse) {
      setErrorPhone('Please enter a valid phone number.')
      setSendingPhoneOTP(false)
      return
    }

    try {
      await sendPhoneOTP(email, phoneToUse)
      setSuccessPhone(`Verification code sent to ${phoneToUse}`)
      setPhoneNumber(phoneToUse)
      setIsEditingPhone(false)
      setPhoneCooldown(60) // 1-minute resend cooldown
    } catch (err: any) {
      setErrorPhone(err.response?.data?.detail || 'Failed to send phone verification code.')
    } finally {
      setSendingPhoneOTP(false)
    }
  }

  // Handle Phone Verification Check
  const handleVerifyPhone = async (e: React.FormEvent) => {
    e.preventDefault()
    setErrorPhone(null)
    setSuccessPhone(null)
    setSubmittingPhone(true)

    try {
      const res = await verifyPhoneOTP(email, phoneCode)
      setSuccessPhone('Phone number verified successfully!')
      setPhoneVerified(true)

      if (res && res.access_token) {
        localStorage.setItem('smartonboard_token', res.access_token)
        handleRedirect()
      } else {
        loadStatus(email)
      }
    } catch (err: any) {
      setErrorPhone(err.response?.data?.detail || 'Failed to verify phone code.')
    } finally {
      setSubmittingPhone(false)
    }
  }

  // Safe email submission if they landed without email state
  const handleEmailSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (email.trim()) {
      localStorage.setItem('smartonboard_verify_email', email.trim())
      loadStatus(email.trim())
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

  const cardStyle: React.CSSProperties = {
    flex: 1,
    border: '1px solid var(--border)',
    borderRadius: 12,
    padding: 24,
    background: 'transparent',
    display: 'flex',
    flexDirection: 'column',
    justifyContent: 'space-between',
    minHeight: 280,
  }

  const buttonStyle = (disabled: boolean): React.CSSProperties => ({
    width: '100%',
    padding: '12px 24px',
    background: 'var(--color-ink)',
    color: 'var(--color-pure-white)',
    border: 'none',
    borderRadius: 'var(--radius-buttons)',
    fontSize: 13,
    fontWeight: 500,
    fontFamily: "var(--font-sans)",
    cursor: disabled ? 'not-allowed' : 'pointer',
    opacity: disabled ? 0.6 : 1,
    transition: 'opacity 0.15s ease',
  })

  // 1. Loading State
  if (!statusLoaded) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--bg)' }}>
        <div className="spinner spinner--lg" />
      </div>
    )
  }

  // 2. Missing Email State (No state preserved yet)
  if (!email) {
    return (
      <div style={{ minHeight: '100vh', background: 'var(--bg)', color: 'var(--text)', fontFamily: 'var(--font-sans)' }}>
        <nav style={{ height: 56, display: 'flex', alignItems: 'center', padding: '0 24px', borderBottom: '1px solid var(--border)' }}>
          <Link to="/" style={{ fontSize: 18, fontWeight: 500, color: 'var(--text)', textDecoration: 'none' }}>SmartOnboard</Link>
        </nav>
        <div style={{ maxWidth: 400, margin: '0 auto', padding: '120px 24px' }}>
          <h1 style={{ fontSize: 24, fontWeight: 500, margin: 0 }}>Restore Verification</h1>
          <p style={{ fontSize: 14, color: 'var(--text-secondary)', margin: '8px 0 24px' }}>
            Please enter your registered email address to check your verification status and continue onboarding.
          </p>
          <form onSubmit={handleEmailSubmit} style={{ border: '1px solid var(--border)', borderRadius: 12, padding: 24 }}>
            <div style={{ marginBottom: 20 }}>
              <label htmlFor="email" style={labelStyle}>Email Address</label>
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
            <button type="submit" style={buttonStyle(!email.trim())}>Check Status</button>
          </form>
        </div>
      </div>
    )
  }

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)', color: 'var(--text)', fontFamily: 'var(--font-sans)' }}>
      {/* Top Nav */}
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
        <button
          onClick={() => {
            localStorage.removeItem('smartonboard_token')
            localStorage.removeItem('smartonboard_verify_email')
            navigate('/candidate/login')
          }}
          style={{ background: 'none', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer', fontSize: 14 }}
        >
          Cancel & Exit
        </button>
      </nav>

      {/* Main Panel Container */}
      <div style={{ maxWidth: emailVerified ? 450 : 900, margin: '0 auto', padding: '80px 24px 48px' }}>
        <h1 style={{ fontSize: 29, fontWeight: 500, lineHeight: 1.1, color: 'var(--text)', margin: 0 }}>
          Verify Your Profile
        </h1>
        <p style={{ fontSize: 14, color: 'var(--text-secondary)', margin: '8px 0 32px' }}>
          Onboarding verification is required before you can access the career dashboard. Email: <strong>{email}</strong>
        </p>

        {/* Dynamic Multi-Panel Layout */}
        <div style={{ display: 'flex', flexDirection: 'row', gap: 24, flexWrap: 'wrap' }}>
          
          {/* Panel 1: Email Verification (Only shown if email is not yet verified) */}
          {!emailVerified && (
            <div style={cardStyle}>
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                  <h2 style={{ fontSize: 18, fontWeight: 500, margin: 0 }}>1. Email Verification</h2>
                  <span style={{ fontSize: 11, padding: '2px 8px', borderRadius: 12, background: '#fee2e2', color: '#ef4444', fontWeight: 500 }}>Unverified</span>
                </div>
                <p style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.4, marginBottom: 20 }}>
                  Enter the 6-digit verification code sent to your email by Resend.
                </p>

                {errorEmail && (
                  <div style={{ border: '1px solid var(--danger)', borderRadius: 8, padding: '8px 12px', marginBottom: 16, color: 'var(--danger)', fontSize: 12 }}>
                    {errorEmail}
                  </div>
                )}
                {successEmail && (
                  <div style={{ border: '1px solid #22c55e', borderRadius: 8, padding: '8px 12px', marginBottom: 16, color: '#22c55e', fontSize: 12, background: 'transparent' }}>
                    {successEmail}
                  </div>
                )}
              </div>

              <form onSubmit={handleVerifyEmail}>
                <div style={{ marginBottom: 20 }}>
                  <label htmlFor="emailCode" style={labelStyle}>Email Verification Code</label>
                  <input
                    id="emailCode"
                    type="text"
                    required
                    maxLength={6}
                    value={emailCode}
                    onChange={e => setEmailCode(e.target.value.replace(/\D/g, ''))}
                    placeholder="000000"
                    style={{ ...inputStyle, letterSpacing: '0.3em', textAlign: 'center', fontSize: 20 }}
                  />
                </div>
                <button type="submit" disabled={submittingEmail || emailCode.length !== 6} style={buttonStyle(submittingEmail || emailCode.length !== 6)}>
                  {submittingEmail ? 'Verifying Email…' : 'Verify Email'}
                </button>
              </form>
            </div>
          )}

          {/* Panel 2: Phone Verification (Always shown. Prompts for number if missing) */}
          <div style={cardStyle}>
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                <h2 style={{ fontSize: 18, fontWeight: 500, margin: 0 }}>
                  {emailVerified ? 'Verify Your Phone Number' : '2. Phone Verification'}
                </h2>
                <span style={{
                  fontSize: 11,
                  padding: '2px 8px',
                  borderRadius: 12,
                  background: phoneVerified ? '#dcfce7' : '#fee2e2',
                  color: phoneVerified ? '#22c55e' : '#ef4444',
                  fontWeight: 500
                }}>
                  {phoneVerified ? 'Verified' : 'Unverified'}
                </span>
              </div>

              {errorPhone && (
                <div style={{ border: '1px solid var(--danger)', borderRadius: 8, padding: '8px 12px', marginBottom: 16, color: 'var(--danger)', fontSize: 12 }}>
                  {errorPhone}
                </div>
              )}
              {successPhone && (
                <div style={{ border: '1px solid #22c55e', borderRadius: 8, padding: '8px 12px', marginBottom: 16, color: '#22c55e', fontSize: 12, background: 'transparent' }}>
                  {successPhone}
                </div>
              )}

              {/* A. If phone number is not registered yet */}
              {!phoneNumber && !isEditingPhone && (
                <div>
                  <p style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.4, marginBottom: 20 }}>
                    Provide a valid mobile phone number to receive a Twilio SMS verification code.
                  </p>
                  <form onSubmit={handleSendPhoneOTP}>
                    <div style={{ marginBottom: 20 }}>
                      <label htmlFor="phoneInput" style={labelStyle}>Phone Number</label>
                      <input
                        id="phoneInput"
                        type="tel"
                        required
                        value={newPhone}
                        onChange={e => setNewPhone(e.target.value)}
                        placeholder="+15551234567"
                        style={inputStyle}
                      />
                    </div>
                    <button type="submit" disabled={sendingPhoneOTP || !newPhone} style={buttonStyle(sendingPhoneOTP || !newPhone)}>
                      {sendingPhoneOTP ? 'Sending OTP…' : 'Send Verification Code'}
                    </button>
                  </form>
                </div>
              )}

              {/* B. If phone number is registered but needs verification (allows editing/changing phone number) */}
              {phoneNumber && !phoneVerified && (
                <div>
                  {isEditingPhone ? (
                    <form onSubmit={handleSendPhoneOTP}>
                      <p style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.4, marginBottom: 20 }}>
                        Enter your new phone number to receive a fresh verification code.
                      </p>
                      <div style={{ marginBottom: 20 }}>
                        <label htmlFor="newPhoneInput" style={labelStyle}>New Phone Number</label>
                        <input
                          id="newPhoneInput"
                          type="tel"
                          required
                          value={newPhone}
                          onChange={e => setNewPhone(e.target.value)}
                          placeholder="+15551234567"
                          style={inputStyle}
                        />
                      </div>
                      <div style={{ display: 'flex', gap: 12 }}>
                        <button type="submit" disabled={sendingPhoneOTP || !newPhone} style={buttonStyle(sendingPhoneOTP || !newPhone)}>
                          {sendingPhoneOTP ? 'Updating…' : 'Send Fresh OTP'}
                        </button>
                        <button
                          type="button"
                          onClick={() => {
                            setNewPhone(phoneNumber)
                            setIsEditingPhone(false)
                          }}
                          style={{
                            background: 'none',
                            border: '1px solid var(--border)',
                            borderRadius: 'var(--radius-buttons)',
                            padding: '12px 16px',
                            color: 'var(--text)',
                            fontSize: 13,
                            cursor: 'pointer'
                          }}
                        >
                          Cancel
                        </button>
                      </div>
                    </form>
                  ) : (
                    <div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
                        <span style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
                          Code sent to: <strong>{phoneNumber}</strong>
                        </span>
                        <button
                          onClick={() => setIsEditingPhone(true)}
                          style={{ background: 'none', border: 'none', color: 'var(--accent)', textDecoration: 'underline', cursor: 'pointer', fontSize: 12 }}
                        >
                          Change Number
                        </button>
                      </div>

                      <form onSubmit={handleVerifyPhone}>
                        <div style={{ marginBottom: 20 }}>
                          <label htmlFor="phoneCode" style={labelStyle}>SMS Verification Code</label>
                          <input
                            id="phoneCode"
                            type="text"
                            required
                            maxLength={6}
                            value={phoneCode}
                            onChange={e => setPhoneCode(e.target.value.replace(/\D/g, ''))}
                            placeholder="000000"
                            style={{ ...inputStyle, letterSpacing: '0.3em', textAlign: 'center', fontSize: 20 }}
                          />
                        </div>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                          <button type="submit" disabled={submittingPhone || phoneCode.length !== 6} style={buttonStyle(submittingPhone || phoneCode.length !== 6)}>
                            {submittingPhone ? 'Verifying Code…' : 'Verify & Activate Profile'}
                          </button>
                          <button
                            type="button"
                            disabled={phoneCooldown > 0 || sendingPhoneOTP}
                            onClick={() => handleSendPhoneOTP()}
                            style={{
                              background: 'none',
                              border: 'none',
                              color: phoneCooldown > 0 ? 'var(--text-secondary)' : 'var(--accent)',
                              textDecoration: 'underline',
                              cursor: phoneCooldown > 0 ? 'not-allowed' : 'pointer',
                              fontSize: 12,
                              textAlign: 'center'
                            }}
                          >
                            {phoneCooldown > 0 ? `Resend OTP in ${phoneCooldown}s` : 'Resend SMS OTP'}
                          </button>
                        </div>
                      </form>
                    </div>
                  )}
                </div>
              )}

              {/* C. If phone is verified */}
              {phoneVerified && (
                <div style={{ padding: '20px 0', textAlign: 'center' }}>
                  <div style={{ fontSize: 40, color: '#22c55e', marginBottom: 12 }}>✓</div>
                  <p style={{ fontSize: 14, color: 'var(--text-secondary)' }}>
                    Your phone number has been verified.
                  </p>
                </div>
              )}
            </div>
          </div>

        </div>
      </div>
    </div>
  )
}
