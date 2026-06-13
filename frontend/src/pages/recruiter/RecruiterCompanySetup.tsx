import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import '../../App.css'

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
    <div className="container" style={{ maxWidth: '480px', padding: 'var(--space-32) var(--space-16)' }}>
      <div className="card" style={{ padding: 'var(--space-32)' }}>
        <h1 className="h2" style={{ marginBottom: 'var(--space-8)', textAlign: 'center' }}>
          Company Setup Wizard
        </h1>
        <p className="text-secondary" style={{ marginBottom: 'var(--space-24)', textAlign: 'center' }}>
          Please complete your corporate profile to start publishing jobs and reviewing candidates.
        </p>

        {error && (
          <div className="alert alert--error" style={{ marginBottom: 'var(--space-16)' }}>
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-16)' }}>
          <div className="form-group">
            <label className="form-label" htmlFor="company-name">Company Name</label>
            <input
              className="form-input"
              id="company-name"
              type="text"
              placeholder="e.g. Acme Corp"
              value={companyName}
              onChange={(e) => setCompanyName(e.target.value)}
              required
              disabled={loading}
            />
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="company-website">Company Website</label>
            <input
              className="form-input"
              id="company-website"
              type="url"
              placeholder="e.g. https://acme.com"
              value={website}
              onChange={(e) => setWebsite(e.target.value)}
              required
              disabled={loading}
            />
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="company-domain">Verified Corporate Domain</label>
            <input
              className="form-input"
              id="company-domain"
              type="text"
              value={domain}
              readOnly
              style={{ backgroundColor: 'var(--color-bg-tertiary)', cursor: 'not-allowed' }}
              disabled
            />
            <span className="text-secondary" style={{ fontSize: 'var(--font-size-sm)', marginTop: 'var(--space-4)', display: 'block' }}>
              Prefilled and locked to match your authenticated email domain.
            </span>
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="company-industry">Industry</label>
            <input
              className="form-input"
              id="company-industry"
              type="text"
              placeholder="e.g. Technology, Healthcare"
              value={industry}
              onChange={(e) => setIndustry(e.target.value)}
              required
              disabled={loading}
            />
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="company-size">Company Size</label>
            <select
              className="form-input"
              id="company-size"
              value={companySize}
              onChange={(e) => setCompanySize(e.target.value)}
              disabled={loading}
              style={{ width: '100%' }}
            >
              <option value="1-10">1-10 employees</option>
              <option value="11-50">11-50 employees</option>
              <option value="51-200">51-200 employees</option>
              <option value="201-500">201-500 employees</option>
              <option value="501+">501+ employees</option>
            </select>
          </div>

          <button
            className="btn btn--primary"
            type="submit"
            disabled={loading}
            style={{ width: '100%', marginTop: 'var(--space-8)' }}
          >
            {loading ? 'Creating Profile...' : 'Complete Registration'}
          </button>
        </form>
      </div>
    </div>
  )
}
