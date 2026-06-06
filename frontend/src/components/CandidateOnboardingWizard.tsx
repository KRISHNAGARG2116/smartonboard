import { useState } from 'react'

interface CandidateOnboardingWizardProps {
  onComplete: () => void
}

export default function CandidateOnboardingWizard({ onComplete }: CandidateOnboardingWizardProps) {
  const [step, setStep] = useState(1)
  const [bio, setBio] = useState('')
  const [resumeName, setResumeName] = useState('')
  const [emailOtp, setEmailOtp] = useState('')
  const [phoneOtp, setPhoneOtp] = useState('')
  const [skills, setSkills] = useState('React, TypeScript, CSS')

  const handleNext = () => {
    if (step < 6) {
      setStep(prev => prev + 1)
    } else {
      onComplete()
    }
  }

  const inputStyle: React.CSSProperties = {
    width: '100%',
    background: 'transparent',
    border: 'none',
    borderBottom: '1px solid var(--color-warm-cream)',
    borderRadius: 0,
    padding: '8px 0',
    fontSize: 15,
    color: '#ffedd7',
    outline: 'none',
    boxSizing: 'border-box',
    marginTop: 8
  }

  return (
    <div style={{
      position: 'fixed',
      inset: 0,
      background: '#100904',
      zIndex: 2000,
      display: 'grid',
      placeItems: 'center',
      padding: 24,
      fontFamily: "'Plus Jakarta Sans', sans-serif"
    }}>
      <div style={{
        maxWidth: 500,
        width: '100%',
        border: '1px solid var(--color-warm-cream)',
        borderRadius: 12,
        padding: 40,
        boxSizing: 'border-box'
      }}>
        {/* Stepper progress */}
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, color: 'var(--text-secondary)', letterSpacing: '0.05em', marginBottom: 24 }}>
          <span>CANDIDATE ONBOARDING</span>
          <span>STEP {step} OF 6</span>
        </div>

        {/* Step Content */}
        {step === 1 && (
          <div>
            <h2 style={{ fontSize: 24, fontWeight: 500, color: '#ffedd7', margin: '0 0 8px' }}>Create Profile bio</h2>
            <p style={{ fontSize: 14, color: 'var(--text-secondary)', lineHeight: 1.33, margin: '0 0 24px' }}>
              Briefly describe your career focus and primary programming background.
            </p>
            <label style={{ fontSize: 10, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Professional Statement
            </label>
            <input 
              required
              value={bio}
              onChange={e => setBio(e.target.value)}
              placeholder="e.g. Frontend Engineer specializing in single-page React apps" 
              style={inputStyle} 
            />
          </div>
        )}

        {step === 2 && (
          <div>
            <h2 style={{ fontSize: 24, fontWeight: 500, color: '#ffedd7', margin: '0 0 8px' }}>Upload Primary Resume</h2>
            <p style={{ fontSize: 14, color: 'var(--text-secondary)', lineHeight: 1.33, margin: '0 0 24px' }}>
              Load your first parsed resume file to establish matching keywords.
            </p>
            <label style={{ fontSize: 10, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Resume Filename
            </label>
            <input 
              required
              value={resumeName}
              onChange={e => setResumeName(e.target.value)}
              placeholder="e.g. my_resume_2026.pdf" 
              style={inputStyle} 
            />
          </div>
        )}

        {step === 3 && (
          <div>
            <h2 style={{ fontSize: 24, fontWeight: 500, color: '#ffedd7', margin: '0 0 8px' }}>Verify Email OTP</h2>
            <p style={{ fontSize: 14, color: 'var(--text-secondary)', lineHeight: 1.33, margin: '0 0 24px' }}>
              Verify your profile email authentication state.
            </p>
            <label style={{ fontSize: 10, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Email verification code
            </label>
            <input 
              required
              value={emailOtp}
              onChange={e => setEmailOtp(e.target.value)}
              placeholder="e.g. 123456" 
              style={inputStyle} 
            />
          </div>
        )}

        {step === 4 && (
          <div>
            <h2 style={{ fontSize: 24, fontWeight: 500, color: '#ffedd7', margin: '0 0 8px' }}>Verify Phone SMS OTP</h2>
            <p style={{ fontSize: 14, color: 'var(--text-secondary)', lineHeight: 1.33, margin: '0 0 24px' }}>
              Confirm your contact phone identity.
            </p>
            <label style={{ fontSize: 10, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              SMS verification code
            </label>
            <input 
              required
              value={phoneOtp}
              onChange={e => setPhoneOtp(e.target.value)}
              placeholder="e.g. 654321" 
              style={inputStyle} 
            />
          </div>
        )}

        {step === 5 && (
          <div>
            <h2 style={{ fontSize: 24, fontWeight: 500, color: '#ffedd7', margin: '0 0 8px' }}>Confirm Primary Skills</h2>
            <p style={{ fontSize: 14, color: 'var(--text-secondary)', lineHeight: 1.33, margin: '0 0 24px' }}>
              Confirm your key matching keywords and programming experience.
            </p>
            <label style={{ fontSize: 10, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Extracted Skills
            </label>
            <input 
              value={skills}
              onChange={e => setSkills(e.target.value)}
              placeholder="e.g. React, CSS, Node.js" 
              style={inputStyle} 
            />
          </div>
        )}

        {step === 6 && (
          <div>
            <h2 style={{ fontSize: 24, fontWeight: 500, color: '#ffedd7', margin: '0 0 8px' }}>Setup Complete!</h2>
            <p style={{ fontSize: 14, color: 'var(--text-secondary)', lineHeight: 1.33, margin: '0 0 24px' }}>
              Your profile is verified. You are now ready to view recommended roles and submit applications. Let's enter your Career Hub.
            </p>
          </div>
        )}

        {/* Action button */}
        <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 32 }}>
          <button 
            onClick={handleNext}
            className="btn btn--primary" 
            style={{ borderRadius: 36, padding: '12px 32px' }}
          >
            {step === 6 ? 'Enter Dashboard' : 'Next Step'}
          </button>
        </div>
      </div>
    </div>
  )
}
