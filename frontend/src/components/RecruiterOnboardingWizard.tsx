import { useState } from 'react'

interface RecruiterOnboardingWizardProps {
  onComplete: () => void
}

export default function RecruiterOnboardingWizard({ onComplete }: RecruiterOnboardingWizardProps) {
  const [step, setStep] = useState(1)
  const [companyName, setCompanyName] = useState('')
  const [jobTitle, setJobTitle] = useState('')
  const [pipelineType, setPipelineType] = useState('Standard Technical')
  const [teamEmail, setTeamEmail] = useState('')

  const handleNext = () => {
    if (step < 5) {
      setStep(prev => prev + 1)
    } else {
      onComplete()
    }
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
    outline: 'none',
    boxSizing: 'border-box',
    marginTop: 8
  }

  return (
    <div style={{
      position: 'fixed',
      inset: 0,
      background: 'var(--bg)',
      zIndex: 2000,
      display: 'grid',
      placeItems: 'center',
      padding: 24,
      fontFamily: "var(--font-sans)"
    }}>
      <div style={{
        maxWidth: 500,
        width: '100%',
        border: '1px solid var(--border)',
        borderRadius: 12,
        padding: 40,
        boxSizing: 'border-box'
      }}>
        {/* Stepper progress */}
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, color: 'var(--text-secondary)', letterSpacing: '0.05em', marginBottom: 24 }}>
          <span>RECRUITER ONBOARDING</span>
          <span>STEP {step} OF 5</span>
        </div>

        {/* Step Content */}
        {step === 1 && (
          <div>
            <h2 style={{ fontSize: 24, fontWeight: 500, color: 'var(--text)', margin: '0 0 8px' }}>Create Company Space</h2>
            <p style={{ fontSize: 14, color: 'var(--text-secondary)', lineHeight: 1.33, margin: '0 0 24px' }}>
              Set up your company details to brand candidate applications.
            </p>
            <label style={{ fontSize: 10, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Organization Name
            </label>
            <input 
              required
              value={companyName}
              onChange={e => setCompanyName(e.target.value)}
              placeholder="e.g. Acme Corporation" 
              style={inputStyle} 
            />
          </div>
        )}

        {step === 2 && (
          <div>
            <h2 style={{ fontSize: 24, fontWeight: 500, color: 'var(--text)', margin: '0 0 8px' }}>Post Your First Job</h2>
            <p style={{ fontSize: 14, color: 'var(--text-secondary)', lineHeight: 1.33, margin: '0 0 24px' }}>
              Add a job opening to start matching candidates immediately.
            </p>
            <label style={{ fontSize: 10, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Job Title
            </label>
            <input 
              required
              value={jobTitle}
              onChange={e => setJobTitle(e.target.value)}
              placeholder="e.g. Senior Backend Engineer" 
              style={inputStyle} 
            />
          </div>
        )}

        {step === 3 && (
          <div>
            <h2 style={{ fontSize: 24, fontWeight: 500, color: 'var(--text)', margin: '0 0 8px' }}>Configure Hiring Pipeline</h2>
            <p style={{ fontSize: 14, color: 'var(--text-secondary)', lineHeight: 1.33, margin: '0 0 24px' }}>
              Define default milestones for review stages.
            </p>
            <label style={{ fontSize: 10, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Pipeline Schema Type
            </label>
            <select 
              value={pipelineType}
              onChange={e => setPipelineType(e.target.value)}
              style={{
                width: '100%',
                background: 'transparent',
                border: 'none',
                borderBottom: '1px solid var(--border)',
                borderRadius: 0,
                padding: '8px 0',
                fontSize: 15,
                color: 'var(--text)',
                outline: 'none',
                cursor: 'pointer',
                marginTop: 8
              }}
            >
              <option value="Standard Technical" style={{ background: 'var(--bg)' }}>Standard Technical (Parsing &rarr; Technical Exam &rarr; Interview)</option>
              <option value="Executive Focus" style={{ background: 'var(--bg)' }}>Executive Focus (Parsing &rarr; Panel Evaluation &rarr; Offer)</option>
              <option value="General Screening" style={{ background: 'var(--bg)' }}>General Screening (Parsing &rarr; Screening Call &rarr; Hire)</option>
            </select>
          </div>
        )}

        {step === 4 && (
          <div>
            <h2 style={{ fontSize: 24, fontWeight: 500, color: 'var(--text)', margin: '0 0 8px' }}>Invite Team Members</h2>
            <p style={{ fontSize: 14, color: 'var(--text-secondary)', lineHeight: 1.33, margin: '0 0 24px' }}>
              Invite co-recruiters to collaborate in this workspace.
            </p>
            <label style={{ fontSize: 10, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Team Member Email
            </label>
            <input 
              value={teamEmail}
              onChange={e => setTeamEmail(e.target.value)}
              placeholder="co-recruiter@company.com" 
              style={inputStyle} 
            />
          </div>
        )}

        {step === 5 && (
          <div>
            <h2 style={{ fontSize: 24, fontWeight: 500, color: 'var(--text)', margin: '0 0 8px' }}>Onboarding Completed!</h2>
            <p style={{ fontSize: 14, color: 'var(--text-secondary)', lineHeight: 1.33, margin: '0 0 24px' }}>
              Your workspace is set up and ready to match candidates. Let's enter your Hiring Command Center.
            </p>
            <div style={{ padding: 16, border: '1px dashed var(--border)', borderRadius: 12, fontSize: 13, color: 'var(--text-secondary)' }}>
              &bull; Company: {companyName || 'Acme Workspace'}<br/>
              &bull; First Job: {jobTitle || 'Senior Developer'}<br/>
              &bull; Schema: {pipelineType}
            </div>
          </div>
        )}

        {/* Action button */}
        <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 32 }}>
          <button 
            onClick={handleNext}
            className="btn btn--primary" 
            style={{ borderRadius: 'var(--radius-buttons)', padding: '12px 32px' }}
          >
            {step === 5 ? 'Enter Dashboard' : 'Next Step'}
          </button>
        </div>
      </div>
    </div>
  )
}
