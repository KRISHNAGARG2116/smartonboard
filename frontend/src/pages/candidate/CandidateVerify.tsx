import { useState, useEffect } from 'react'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import {
  getVerificationStatus,
  sendPhoneOTP,
  verifyPhoneOTP,
  verifyEmailOTP
} from '../../api'
import SteepCard from '../../components/design-system/SteepCard'
import SteepInput from '../../components/design-system/SteepInput'
import SteepButton from '../../components/design-system/SteepButton'
import SteepBadge from '../../components/design-system/SteepBadge'

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
    let targetEmail = (location.state as any)?.email || ''

    if (!targetEmail) {
      const params = new URLSearchParams(location.search)
      targetEmail = params.get('email') || ''
    }

    if (!targetEmail) {
      targetEmail = localStorage.getItem('smartonboard_verify_email') || ''
    }

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

      if (data.email_verified && data.phone_verified) {
        handleRedirect()
      }
    } catch (err: any) {
      setErrorEmail(err.response?.data?.detail || 'Failed to fetch verification status.')
    } finally {
      setStatusLoaded(true)
    }
  }

  const handleRedirect = () => {
    const target = localStorage.getItem('smartonboard_redirect_target')
    if (target) {
      localStorage.removeItem('smartonboard_redirect_target')
      window.location.href = target
    } else {
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

      if (res && res.access_token) {
        localStorage.setItem('smartonboard_token', res.access_token)
        handleRedirect()
      } else {
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
      setPhoneCooldown(60)
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

  const handleEmailSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (email.trim()) {
      localStorage.setItem('smartonboard_verify_email', email.trim())
      loadStatus(email.trim())
    }
  }

  // 1. Loading State
  if (!statusLoaded) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--color-fog)' }}>
        <div className="spinner spinner--lg" />
      </div>
    )
  }

  // 2. Missing Email State
  if (!email) {
    return (
      <div className="app-shell" style={{ background: 'var(--color-fog)' }}>
        <nav
          style={{
            height: 'var(--header-h)',
            display: 'flex',
            alignItems: 'center',
            paddingInline: 'var(--spacing-24)',
            borderBottom: '1px solid var(--border)',
            background: 'var(--color-pure-white)'
          }}
        >
          <Link to="/" style={{ fontSize: 'var(--text-body-lg)', fontWeight: 500, color: 'var(--color-ink)' }}>
            SmartOnboard
          </Link>
        </nav>
        <div style={{ maxWidth: '400px', margin: '0 auto', padding: 'var(--spacing-80) var(--spacing-24)' }}>
          <h1 className="font-signifier" style={{ fontSize: 'var(--text-heading-sm)', color: 'var(--color-ink)', margin: 0, textAlign: 'left' }}>
            Restore Verification
          </h1>
          <p style={{ fontSize: 'var(--text-caption)', color: 'var(--color-ash)', margin: 'var(--spacing-8) 0 var(--spacing-24)', textAlign: 'left' }}>
            Please enter your registered email address to check your verification status and continue onboarding.
          </p>
          <form onSubmit={handleEmailSubmit}>
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
              <SteepButton type="submit" disabled={!email.trim()} variant="primary" block>
                Check Status
              </SteepButton>
            </SteepCard>
          </form>
        </div>
      </div>
    )
  }

  return (
    <div className="app-shell" style={{ background: 'var(--color-fog)' }}>
      {/* Top Nav */}
      <nav
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          height: 'var(--header-h)',
          paddingInline: 'var(--spacing-24)',
          borderBottom: '1px solid var(--border)',
          background: 'var(--color-pure-white)'
        }}
      >
        <Link to="/" style={{ fontSize: 'var(--text-body-lg)', fontWeight: 500, color: 'var(--color-ink)' }}>
          SmartOnboard
        </Link>
        <SteepButton
          variant="ghost"
          size="sm"
          onClick={() => {
            localStorage.removeItem('smartonboard_token')
            localStorage.removeItem('smartonboard_verify_email')
            navigate('/candidate/login')
          }}
        >
          Cancel & Exit
        </SteepButton>
      </nav>

      {/* Main Panel Container */}
      <div style={{ maxWidth: emailVerified ? '450px' : '900px', margin: '0 auto', padding: 'var(--spacing-80) var(--spacing-24) var(--spacing-48)' }}>
        <h1 className="font-signifier" style={{ fontSize: 'var(--text-heading-sm)', color: 'var(--color-ink)', margin: 0, textAlign: 'left' }}>
          Verify Your Profile
        </h1>
        <p style={{ fontSize: 'var(--text-caption)', color: 'var(--color-ash)', margin: 'var(--spacing-8) 0 var(--spacing-32)', textAlign: 'left' }}>
          Onboarding verification is required before you can access the career dashboard. Email: <strong>{email}</strong>
        </p>

        {/* Dynamic Multi-Panel Layout */}
        <div style={{ display: 'flex', gap: 'var(--spacing-24)', flexDirection: 'row', flexWrap: 'wrap' }}>
          
          {/* Panel 1: Email Verification */}
          {!emailVerified && (
            <div style={{ flex: '1 1 340px' }}>
              <SteepCard style={{ minHeight: '340px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--spacing-16)' }}>
                    <h2 style={{ fontSize: 'var(--text-body-lg)', fontWeight: 500, color: 'var(--color-ink)', margin: 0 }}>
                      1. Email Verification
                    </h2>
                    <SteepBadge variant="danger">Unverified</SteepBadge>
                  </div>
                  <p style={{ fontSize: 'var(--text-caption)', color: 'var(--color-ash)', lineHeight: 1.4, marginBottom: 'var(--spacing-20)' }}>
                    Enter the 6-digit verification code sent to your email by Resend.
                  </p>

                  {errorEmail && (
                    <div className="banner banner--error" role="alert" style={{ marginBottom: 'var(--spacing-16)', fontSize: 'var(--text-caption)' }}>
                      {errorEmail}
                    </div>
                  )}
                  {successEmail && (
                    <div className="banner banner--success" role="alert" style={{ marginBottom: 'var(--spacing-16)', fontSize: 'var(--text-caption)' }}>
                      {successEmail}
                    </div>
                  )}
                </div>

                <form onSubmit={handleVerifyEmail}>
                  <div className="form-group" style={{ marginBottom: 'var(--spacing-16)' }}>
                    <label htmlFor="emailCode" className="form-label">Email Verification Code</label>
                    <input
                      id="emailCode"
                      type="text"
                      required
                      maxLength={6}
                      value={emailCode}
                      onChange={e => setEmailCode(e.target.value.replace(/\D/g, ''))}
                      placeholder="000000"
                      className="otp-input"
                    />
                  </div>
                  <SteepButton type="submit" disabled={submittingEmail || emailCode.length !== 6} variant="primary" block>
                    {submittingEmail ? 'Verifying Email…' : 'Verify Email'}
                  </SteepButton>
                </form>
              </SteepCard>
            </div>
          )}

          {/* Panel 2: Phone Verification */}
          <div style={{ flex: '1 1 340px' }}>
            <SteepCard style={{ minHeight: '340px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', flexDirection: 'column', flex: 1, justifyContent: 'space-between' }}>
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--spacing-16)' }}>
                    <h2 style={{ fontSize: 'var(--text-body-lg)', fontWeight: 500, color: 'var(--color-ink)', margin: 0 }}>
                      {emailVerified ? 'Verify Your Phone Number' : '2. Phone Verification'}
                    </h2>
                    <SteepBadge variant={phoneVerified ? 'success' : 'danger'}>
                      {phoneVerified ? 'Verified' : 'Unverified'}
                    </SteepBadge>
                  </div>

                  {errorPhone && (
                    <div className="banner banner--error" role="alert" style={{ marginBottom: 'var(--spacing-16)', fontSize: 'var(--text-caption)' }}>
                      {errorPhone}
                    </div>
                  )}
                  {successPhone && (
                    <div className="banner banner--success" role="alert" style={{ marginBottom: 'var(--spacing-16)', fontSize: 'var(--text-caption)' }}>
                      {successPhone}
                    </div>
                  )}

                  {/* A. If phone number is not registered yet */}
                  {!phoneNumber && !isEditingPhone && (
                    <div>
                      <p style={{ fontSize: 'var(--text-caption)', color: 'var(--color-ash)', lineHeight: 1.4, marginBottom: 'var(--spacing-20)' }}>
                        Provide a valid mobile phone number to receive a Twilio SMS verification code.
                      </p>
                      <form onSubmit={handleSendPhoneOTP}>
                        <SteepInput
                          id="phoneInput"
                          type="tel"
                          required
                          value={newPhone}
                          onChange={e => setNewPhone(e.target.value)}
                          placeholder="+15551234567"
                          label="Phone Number"
                        />
                        <SteepButton type="submit" disabled={sendingPhoneOTP || !newPhone} variant="primary" block style={{ marginTop: 'var(--spacing-12)' }}>
                          {sendingPhoneOTP ? 'Sending OTP…' : 'Send Verification Code'}
                        </SteepButton>
                      </form>
                    </div>
                  )}

                  {/* B. If phone number is registered but needs verification */}
                  {phoneNumber && !phoneVerified && (
                    <div>
                      {isEditingPhone ? (
                        <form onSubmit={handleSendPhoneOTP}>
                          <p style={{ fontSize: 'var(--text-caption)', color: 'var(--color-ash)', lineHeight: 1.4, marginBottom: 'var(--spacing-20)' }}>
                            Enter your new phone number to receive a fresh verification code.
                          </p>
                          <SteepInput
                            id="newPhoneInput"
                            type="tel"
                            required
                            value={newPhone}
                            onChange={e => setNewPhone(e.target.value)}
                            placeholder="+15551234567"
                            label="New Phone Number"
                          />
                          <div style={{ display: 'flex', gap: 'var(--spacing-12)', marginTop: 'var(--spacing-16)' }}>
                            <SteepButton type="submit" disabled={sendingPhoneOTP || !newPhone} variant="primary" style={{ flex: 1 }}>
                              {sendingPhoneOTP ? 'Updating…' : 'Send Fresh OTP'}
                            </SteepButton>
                            <SteepButton
                              type="button"
                              onClick={() => {
                                setNewPhone(phoneNumber)
                                setIsEditingPhone(false)
                              }}
                              variant="secondary"
                            >
                              Cancel
                            </SteepButton>
                          </div>
                        </form>
                      ) : (
                        <div>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--spacing-20)' }}>
                            <span style={{ fontSize: 'var(--text-caption)', color: 'var(--color-ash)' }}>
                              Code sent to: <strong>{phoneNumber}</strong>
                            </span>
                            <SteepButton
                              variant="secondary"
                              size="sm"
                              onClick={() => setIsEditingPhone(true)}
                              style={{ padding: 0, textDecoration: 'underline' }}
                            >
                              Change Number
                            </SteepButton>
                          </div>

                          <form onSubmit={handleVerifyPhone}>
                            <div className="form-group" style={{ marginBottom: 'var(--spacing-16)' }}>
                              <label htmlFor="phoneCode" className="form-label">SMS Verification Code</label>
                              <input
                                id="phoneCode"
                                type="text"
                                required
                                maxLength={6}
                                value={phoneCode}
                                onChange={e => setPhoneCode(e.target.value.replace(/\D/g, ''))}
                                placeholder="000000"
                                className="otp-input"
                              />
                            </div>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-12)' }}>
                              <SteepButton type="submit" disabled={submittingPhone || phoneCode.length !== 6} variant="primary" block>
                                {submittingPhone ? 'Verifying Code…' : 'Verify & Activate Profile'}
                              </SteepButton>
                              <SteepButton
                                type="button"
                                disabled={phoneCooldown > 0 || sendingPhoneOTP}
                                onClick={() => handleSendPhoneOTP()}
                                variant="ghost"
                                style={{
                                  width: '100%',
                                  color: phoneCooldown > 0 ? 'var(--color-graphite)' : 'var(--color-rust)',
                                }}
                              >
                                {phoneCooldown > 0 ? `Resend OTP in ${phoneCooldown}s` : 'Resend SMS OTP'}
                              </SteepButton>
                            </div>
                          </form>
                        </div>
                      )}
                    </div>
                  )}

                  {/* C. If phone is verified */}
                  {phoneVerified && (
                    <div style={{ padding: 'var(--spacing-20) 0', textAlign: 'center' }}>
                      <div style={{ fontSize: '36px', color: 'var(--success)', marginBottom: 'var(--spacing-12)' }}>✓</div>
                      <p style={{ fontSize: 'var(--text-caption)', color: 'var(--color-ash)' }}>
                        Your phone number has been verified.
                      </p>
                    </div>
                  )}
                </div>
              </div>
            </SteepCard>
          </div>

        </div>
      </div>
    </div>
  )
}
