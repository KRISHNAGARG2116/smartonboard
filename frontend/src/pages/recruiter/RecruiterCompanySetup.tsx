import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import SteepCard from '../../components/design-system/SteepCard'
import SteepInput from '../../components/design-system/SteepInput'
import SteepButton from '../../components/design-system/SteepButton'
import { createJob } from '../../api'

export default function RecruiterCompanySetup() {
  const { user, setupCompany } = useAuth()
  const navigate = useNavigate()

  // 1. Wizard step restoration
  const [step, setStep] = useState<number>(() => {
    const saved = localStorage.getItem('recruiter_onboarding_step')
    if (saved && saved !== 'completed') {
      const parsed = parseInt(saved, 10)
      if (parsed >= 1 && parsed <= 5) return parsed
    }
    return 1
  })

  // 2. Form state fields
  const [companyName, setCompanyName] = useState('')
  const [website, setWebsite] = useState('')
  const [domain, setDomain] = useState('')
  const [industry, setIndustry] = useState('')
  const [companySize, setCompanySize] = useState('11-50')
  const [jobTitle, setJobTitle] = useState('')
  const [pipelineType, setPipelineType] = useState('Standard Technical')
  const [teamEmail, setTeamEmail] = useState('')

  // 3. UI states
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [serverError, setServerError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  // Auto-extract domain from recruiter's corporate email
  useEffect(() => {
    if (user?.email) {
      const parts = user.email.split('@')
      if (parts.length === 2) {
        setDomain(parts[1].toLowerCase())
      }
    }
  }, [user])

  // Persistence of current step index
  useEffect(() => {
    localStorage.setItem('recruiter_onboarding_step', step.toString())
  }, [step])

  const handleNext = async () => {
    setServerError(null)
    setErrors({})

    if (step === 1) {
      // Validate Step 1: Corporate Profile
      const stepErrors: Record<string, string> = {}
      if (!companyName.trim()) {
        stepErrors.companyName = 'Company Name is required.'
      }
      if (!website.trim()) {
        stepErrors.website = 'Company Website is required.'
      } else if (!website.startsWith('http://') && !website.startsWith('https://')) {
        stepErrors.website = 'Website must start with http:// or https://'
      } else if (website.indexOf('.') === -1) {
        stepErrors.website = 'Invalid website format.'
      }
      if (!industry.trim()) {
        stepErrors.industry = 'Industry is required.'
      }

      if (Object.keys(stepErrors).length > 0) {
        setErrors(stepErrors)
        // Focus the first invalid field
        const firstKey = Object.keys(stepErrors)[0]
        const elementId =
          firstKey === 'companyName'
            ? 'company-name'
            : firstKey === 'website'
            ? 'company-website'
            : 'company-industry'
        document.getElementById(elementId)?.focus()
        return
      }

      // Save company details to server
      setLoading(true)
      try {
        await setupCompany({
          company_name: companyName,
          company_website: website,
          company_domain: domain,
          industry: industry,
          company_size: companySize,
        })
        // Successful save updates the context session. Now advance.
        setStep(2)
      } catch (err: any) {
        const msg = err.response?.data?.detail || 'Failed to setup company. Please check your inputs.'
        setServerError(msg)
      } finally {
        setLoading(false)
      }
    } else if (step === 2) {
      // Validate Step 2: Optional First Job
      if (jobTitle.trim()) {
        setLoading(true)
        try {
          await createJob({
            title: jobTitle,
            department: 'Engineering',
            description: 'First job created during company onboarding.',
            status: 'OPEN',
          })
          setStep(3)
        } catch (err: any) {
          const msg = err.response?.data?.detail || 'Failed to publish job. Please try again.'
          setServerError(msg)
        } finally {
          setLoading(false)
        }
      } else {
        // Skip job creation
        setStep(3)
      }
    } else if (step === 3) {
      setStep(4)
    } else if (step === 4) {
      if (teamEmail.trim()) {
        // Simple regex check for team invitation email
        if (teamEmail.indexOf('@') === -1 || teamEmail.indexOf('.') === -1) {
          setErrors({ teamEmail: 'Please enter a valid email address.' })
          document.getElementById('team-email')?.focus()
          return
        }
        setLoading(true)
        try {
          // Simulate invitation email dispatch
          await new Promise(resolve => setTimeout(resolve, 800))
          setStep(5)
        } catch {
          setServerError('Failed to invite teammate.')
        } finally {
          setLoading(false)
        }
      } else {
        setStep(5)
      }
    }
  }

  const handleFinish = () => {
    localStorage.removeItem('recruiter_onboarding_step')
    navigate('/recruiter/dashboard')
  }



  return (
    <div
      className="app-shell"
      style={{
        background: 'var(--color-fog)',
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      <div style={{ width: '100%', maxWidth: '500px', padding: 'var(--spacing-32) var(--spacing-24)' }}>
        <h1
          className="font-signifier"
          style={{
            fontSize: 'var(--text-heading-sm)',
            color: 'var(--color-ink)',
            textAlign: 'center',
            marginBottom: 'var(--spacing-8)',
            marginTop: 0,
          }}
        >
          Company Onboarding Wizard
        </h1>
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            fontSize: '11px',
            color: 'var(--color-ash)',
            letterSpacing: '0.05em',
            marginBottom: 'var(--spacing-24)',
          }}
        >
          <span>RECRUITER ONBOARDING</span>
          <span>STEP {step} OF 5</span>
        </div>

        {/* Error alert banner */}
        {serverError && (
          <div className="banner banner--error" role="alert" style={{ marginBottom: 'var(--spacing-20)' }}>
            {serverError}
          </div>
        )}

        <SteepCard>
          {/* Step 1: Corporate Profile */}
          {step === 1 && (
            <div>
              <h2 style={{ fontSize: 18, fontWeight: 500, color: 'var(--text)', margin: '0 0 8px' }}>
                Create Company Space
              </h2>
              <p style={{ fontSize: 13, color: 'var(--color-ash)', lineHeight: 1.4, margin: '0 0 20px' }}>
                Set up your workspace parameters. All fields in this profile step are required to advance.
              </p>

              <SteepInput
                id="company-name"
                label="Company Name"
                type="text"
                placeholder="e.g. Acme Corp"
                value={companyName}
                onChange={e => setCompanyName(e.target.value)}
                error={errors.companyName}
                disabled={loading}
              />

              <SteepInput
                id="company-website"
                label="Company Website"
                type="url"
                placeholder="e.g. https://acme.com"
                value={website}
                onChange={e => setWebsite(e.target.value)}
                error={errors.website}
                disabled={loading}
              />

              <SteepInput
                id="company-domain"
                label="Verified Corporate Domain"
                type="text"
                value={domain}
                readOnly
                disabled
                hint="Prefilled to match your email domain."
              />

              <SteepInput
                id="company-industry"
                label="Industry"
                type="text"
                placeholder="e.g. Technology, Finance"
                value={industry}
                onChange={e => setIndustry(e.target.value)}
                error={errors.industry}
                disabled={loading}
              />

              <SteepInput
                id="company-size"
                label="Company Size"
                select
                options={[
                  { value: '1-10', label: '1-10 employees' },
                  { value: '11-50', label: '11-50 employees' },
                  { value: '51-200', label: '51-200 employees' },
                  { value: '201-500', label: '201-500 employees' },
                  { value: '501+', label: '501+ employees' },
                ]}
                value={companySize}
                onChange={e => setCompanySize(e.target.value)}
                disabled={loading}
              />
            </div>
          )}

          {/* Step 2: Post First Job */}
          {step === 2 && (
            <div>
              <h2 style={{ fontSize: 18, fontWeight: 500, color: 'var(--text)', margin: '0 0 8px' }}>
                Post Your First Job
              </h2>
              <p style={{ fontSize: 13, color: 'var(--color-ash)', lineHeight: 1.4, margin: '0 0 20px' }}>
                (Optional) Post a job opening to start matching candidates immediately. Leave blank to skip.
              </p>
              <SteepInput
                id="job-title"
                label="Job Title"
                type="text"
                placeholder="e.g. Senior Backend Engineer"
                value={jobTitle}
                onChange={e => setJobTitle(e.target.value)}
                disabled={loading}
              />
            </div>
          )}

          {/* Step 3: Configure Hiring Pipeline */}
          {step === 3 && (
            <div>
              <h2 style={{ fontSize: 18, fontWeight: 500, color: 'var(--text)', margin: '0 0 8px' }}>
                Configure Hiring Pipeline
              </h2>
              <p style={{ fontSize: 13, color: 'var(--color-ash)', lineHeight: 1.4, margin: '0 0 20px' }}>
                (Optional) Select default stages for your applicant screening queue.
              </p>
              <label className="form-label">Pipeline Schema Type</label>
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
                  color: 'var(--color-ink)',
                  outline: 'none',
                  cursor: 'pointer',
                  marginTop: 8,
                }}
              >
                <option value="Standard Technical">Standard Technical (Parsing &rarr; Exam &rarr; Interview)</option>
                <option value="Executive Focus">Executive Focus (Parsing &rarr; Panel &rarr; Offer)</option>
                <option value="General Screening">General Screening (Parsing &rarr; Phone Call &rarr; Hire)</option>
              </select>
            </div>
          )}

          {/* Step 4: Invite Team Members */}
          {step === 4 && (
            <div>
              <h2 style={{ fontSize: 18, fontWeight: 500, color: 'var(--text)', margin: '0 0 8px' }}>
                Invite Team Members
              </h2>
              <p style={{ fontSize: 13, color: 'var(--color-ash)', lineHeight: 1.4, margin: '0 0 20px' }}>
                (Optional) Invite co-recruiters to collaborate in this workspace. Leave blank to skip.
              </p>
              <SteepInput
                id="team-email"
                label="Team Member Email"
                type="email"
                placeholder="co-recruiter@company.com"
                value={teamEmail}
                onChange={e => setTeamEmail(e.target.value)}
                error={errors.teamEmail}
                disabled={loading}
              />
            </div>
          )}

          {/* Step 5: Onboarding Completed */}
          {step === 5 && (
            <div>
              <h2 style={{ fontSize: 18, fontWeight: 500, color: 'var(--text)', margin: '0 0 8px' }}>
                Workspace Setup Completed!
              </h2>
              <p style={{ fontSize: 13, color: 'var(--color-ash)', lineHeight: 1.4, margin: '0 0 20px' }}>
                Your workspace is ready. Let's enter your Hiring Command Center.
              </p>
              <div
                style={{
                  padding: 16,
                  border: '1px dashed var(--border)',
                  borderRadius: 12,
                  fontSize: 13,
                  color: 'var(--color-ink)',
                  lineHeight: 1.6,
                }}
              >
                &bull; Company: {companyName || 'Acme Workspace'}
                <br />
                &bull; Website: {website}
                <br />
                &bull; Industry: {industry}
                <br />
                &bull; Size: {companySize}
                <br />
                {jobTitle && (
                  <>
                    &bull; First Job: {jobTitle} ({pipelineType})
                    <br />
                  </>
                )}
                {teamEmail && (
                  <>
                    &bull; Invited Teammate: {teamEmail}
                    <br />
                  </>
                )}
              </div>
            </div>
          )}

          {/* Action buttons */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 32 }}>
            <div>
              {step > 1 && step < 5 && (
                <SteepButton onClick={() => setStep(step + 1)} variant="secondary" disabled={loading}>
                  Skip this step
                </SteepButton>
              )}
            </div>
            <div>
              {step < 5 ? (
                <SteepButton onClick={handleNext} disabled={loading} variant="primary">
                  {loading ? 'Processing...' : 'Next Step'}
                </SteepButton>
              ) : (
                <SteepButton onClick={handleFinish} variant="primary">Enter Dashboard</SteepButton>
              )}
            </div>
          </div>
        </SteepCard>
      </div>
    </div>
  )
}
