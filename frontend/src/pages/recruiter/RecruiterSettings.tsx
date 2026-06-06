import { useState, useEffect } from 'react'
import AppLayout from '../../components/AppLayout'
import { fetchCompany, type Company } from '../../api'

export default function RecruiterSettings() {
  const [company, setCompany] = useState<Company | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchCompany()
      .then(co => setCompany(co))
      .catch(err => console.error('Error fetching company details:', err))
      .finally(() => setLoading(false))
  }, [])

  return (
    <AppLayout>
      <div className="container" style={{ padding: 'var(--space-6) 0 var(--space-12)' }}>
        {/* Header */}
        <div style={{
          borderBottom: '1px dashed var(--color-cork-shadow)',
          paddingBottom: 'var(--space-6)',
          marginBottom: 'var(--space-6)'
        }}>
          <span style={{ fontSize: 10, fontWeight: 500, color: 'var(--text-secondary)', letterSpacing: '0.05em', textTransform: 'uppercase' }}>
            Recruiter Control Center
          </span>
          <h1 style={{ fontSize: '29px', fontWeight: 500, letterSpacing: '-0.02em', color: 'var(--text)', margin: '4px 0 0', lineHeight: 1.09 }}>
            Workspace Settings
          </h1>
        </div>

        {loading ? (
          <div style={{ padding: 'var(--space-12) 0', textAlign: 'center', color: 'var(--text-secondary)' }}>
            Loading settings configurations...
          </div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: '3fr 2fr', gap: 'var(--space-6)', alignItems: 'flex-start' }}>
            {/* Main Config Cards */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)' }}>
              
              {/* Profile Config Card */}
              <div style={{
                border: '1px solid var(--color-cork-shadow)',
                borderRadius: 12,
                padding: 'var(--space-6)'
              }}>
                <h2 style={{ fontSize: '18px', fontWeight: 500, margin: '0 0 16px', color: 'var(--text)' }}>
                  Workspace Profile
                </h2>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                  <div>
                    <label style={{ display: 'block', fontSize: 10, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 4 }}>
                      Organization Name
                    </label>
                    <div style={{ fontSize: 15, color: 'var(--text)', paddingBottom: 4, borderBottom: '1px solid var(--color-cork-shadow)' }}>
                      {company?.name || 'ORYZO Recruiting Partner'}
                    </div>
                  </div>
                  <div>
                    <label style={{ display: 'block', fontSize: 10, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 4 }}>
                      Workspace Domain
                    </label>
                    <div style={{ fontSize: 15, color: 'var(--text)', paddingBottom: 4, borderBottom: '1px solid var(--color-cork-shadow)' }}>
                      {company?.slug ? `${company.slug}.com` : 'oryzo.ai'}
                    </div>
                  </div>
                </div>
              </div>

              {/* DNS Verification Center */}
              <div style={{
                border: '1px solid var(--color-cork-shadow)',
                borderRadius: 12,
                padding: 'var(--space-6)'
              }}>
                <h2 style={{ fontSize: '18px', fontWeight: 500, margin: '0 0 16px', color: 'var(--text)' }}>
                  MX / DNS Domain Verification
                </h2>
                <p style={{ fontSize: 14, color: 'var(--text-secondary)', lineHeight: 1.33, margin: '0 0 16px' }}>
                  Verify company email domain records to secure workspace operations and candidate communication channels.
                </p>
                <div style={{
                  border: '1px dashed var(--color-cork-shadow)',
                  borderRadius: 12,
                  padding: 16,
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center'
                }}>
                  <div>
                    <div style={{ fontSize: 14, fontWeight: 500 }}>MX Domain State: <span style={{ color: 'var(--color-burnt-sienna)' }}>Pending Verification</span></div>
                    <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 2 }}>Expected MX domain record: mail.{company?.slug ? `${company.slug}.com` : 'oryzo.ai'}</div>
                  </div>
                  <button className="btn btn--secondary btn--sm" style={{ borderRadius: 22.5 }} onClick={() => alert('Initiating background domain verification check...')}>
                    Verify Records
                  </button>
                </div>
              </div>
            </div>

            {/* Right Sidebar Columns */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)' }}>
              
              {/* Billing Placeholder Card (Option B) */}
              <div style={{
                border: '1px solid var(--color-warm-cream)',
                borderRadius: 12,
                padding: 'var(--space-6)',
                background: 'transparent'
              }}>
                <h2 style={{ fontSize: '18px', fontWeight: 500, margin: '0 0 12px', color: 'var(--text)' }}>
                  Subscription & Billing
                </h2>
                <div style={{
                  fontSize: 10,
                  fontWeight: 500,
                  color: 'var(--color-burnt-sienna)',
                  letterSpacing: '0.05em',
                  textTransform: 'uppercase',
                  marginBottom: 12
                }}>
                  Coming Soon
                </div>
                <p style={{ fontSize: 13, lineHeight: 1.35, color: 'var(--text-secondary)', margin: 0 }}>
                  ORYZO platform subscription controls, invoice tracking, plan selectors, and payment gateway configurations will be made available in the next release cycle.
                </p>
                <div style={{ borderTop: '1px dashed var(--color-cork-shadow)', marginTop: 16, paddingTop: 16, fontSize: 12, color: 'var(--text-secondary)' }}>
                  Planned Plan Rates: <strong>$49/month per active job</strong>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </AppLayout>
  )
}
