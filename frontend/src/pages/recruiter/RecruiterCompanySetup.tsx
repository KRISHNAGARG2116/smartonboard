import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import SteepCard from '../../components/design-system/SteepCard'
import SteepInput from '../../components/design-system/SteepInput'
import SteepButton from '../../components/design-system/SteepButton'

export default function RecruiterCompanySetup() {
  const { user, setupCompany } = useAuth()
  const navigate = useNavigate()

  const [companyName, setCompanyName] = useState('')
  const [website, setWebsite] = useState('')
  const [domain, setDomain] = useState('')
  const [industry, setIndustry] = useState('')
  const [companySize, setCompanySize] = useState('11-50')
  
  const [error, setError] = useState<string | null>(null)
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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)

    // Validation checks
    if (!companyName.trim()) {
      setError('Company Name is required.')
      setLoading(false)
      return
    }
    if (!website.trim()) {
      setError('Company Website is required.')
      setLoading(false)
      return
    }
    if (!industry.trim()) {
      setError('Industry is required.')
      setLoading(false)
      return
    }

    try {
      await setupCompany({
        company_name: companyName,
        company_website: website,
        company_domain: domain,
        industry: industry,
        company_size: companySize,
      })
      // Navigate to dashboard on success
      navigate('/recruiter/dashboard')
    } catch (err: any) {
      const msg = err.response?.data?.detail || 'Failed to setup company. Please try again.'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="app-shell" style={{ background: 'var(--color-fog)', minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div style={{ width: '100%', maxWidth: '480px', padding: 'var(--spacing-32) var(--spacing-24)' }}>
        <h1 className="font-signifier" style={{ fontSize: 'var(--text-heading-sm)', color: 'var(--color-ink)', textAlign: 'center', marginBottom: 'var(--spacing-8)', marginTop: 0 }}>
          Company Setup Wizard
        </h1>
        <p style={{ fontSize: 'var(--text-caption)', color: 'var(--color-ash)', marginBottom: 'var(--spacing-28)', textAlign: 'center' }}>
          Please complete your corporate profile to start publishing jobs and reviewing candidates.
        </p>

        {/* Error banner */}
        {error && (
          <div className="banner banner--error" role="alert" style={{ marginBottom: 'var(--spacing-20)' }}>
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <SteepCard>
            <SteepInput
              id="company-name"
              label="Company Name"
              type="text"
              placeholder="e.g. Acme Corp"
              value={companyName}
              onChange={(e) => setCompanyName(e.target.value)}
              required
              disabled={loading}
            />

            <SteepInput
              id="company-website"
              label="Company Website"
              type="url"
              placeholder="e.g. https://acme.com"
              value={website}
              onChange={(e) => setWebsite(e.target.value)}
              required
              disabled={loading}
            />

            <SteepInput
              id="company-domain"
              label="Verified Corporate Domain"
              type="text"
              value={domain}
              readOnly
              disabled
              hint="Prefilled and locked to match your authenticated email domain."
            />

            <SteepInput
              id="company-industry"
              label="Industry"
              type="text"
              placeholder="e.g. Technology, Healthcare"
              value={industry}
              onChange={(e) => setIndustry(e.target.value)}
              required
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
                { value: '501+', label: '501+ employees' }
              ]}
              value={companySize}
              onChange={(e) => setCompanySize(e.target.value)}
              disabled={loading}
            />

            <SteepButton
              type="submit"
              disabled={loading}
              variant="primary"
              block
              style={{ padding: '12px 20px', marginTop: 'var(--spacing-16)' }}
            >
              {loading ? 'Creating Profile...' : 'Complete Registration'}
            </SteepButton>
          </SteepCard>
        </form>
      </div>
    </div>
  )
}

