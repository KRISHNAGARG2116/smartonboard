import { useState, useEffect } from 'react'
import AppLayout from '../../components/AppLayout'
import { fetchCompany, type Company } from '../../api'
import SteepCard from '../../components/design-system/SteepCard'
import SteepButton from '../../components/design-system/SteepButton'
import SteepInput from '../../components/design-system/SteepInput'
import SteepBadge from '../../components/design-system/SteepBadge'

type SettingsTab = 'profile' | 'recruiters' | 'security' | 'notifications' | 'verification' | 'billing'

export default function RecruiterSettings() {
  const [company, setCompany] = useState<Company | null>(null)
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<SettingsTab>('profile')

  // Notification Preferences State
  const [notifAppReceived, setNotifAppReceived] = useState(true)
  const [notifParsingDone, setNotifParsingDone] = useState(true)
  const [notifInterviewAccepted, setNotifInterviewAccepted] = useState(true)
  const [notifWithdrawn, setNotifWithdrawn] = useState(false)
  const [notifVerifyFail, setNotifVerifyFail] = useState(true)

  useEffect(() => {
    setLoading(true)
    fetchCompany()
      .then(co => setCompany(co))
      .catch(err => console.error('Error fetching company details:', err))
      .finally(() => setLoading(false))
  }, [])

  const tabs: { id: SettingsTab; label: string }[] = [
    { id: 'profile', label: 'Company Profile' },
    { id: 'recruiters', label: 'Recruiters List' },
    { id: 'security', label: 'Security & SSO' },
    { id: 'notifications', label: 'Notifications' },
    { id: 'verification', label: 'DNS Verification' },
    { id: 'billing', label: 'Billing' },
  ]

  return (
    <AppLayout>
      <div className="container" style={{ padding: 'var(--spacing-32) 0 var(--spacing-48)' }}>
        
        {/* Header */}
        <div style={{
          borderBottom: '1px solid var(--border)',
          paddingBottom: 'var(--spacing-24)',
          marginBottom: 'var(--spacing-24)'
        }}>
          <span style={{ fontSize: 'var(--text-caption)', fontWeight: 550, color: 'var(--color-ash)', letterSpacing: '0.05em', textTransform: 'uppercase' }}>
            Recruiter Control Center
          </span>
          <h1 className="font-signifier" style={{ fontSize: 'var(--text-heading-sm)', fontWeight: 500, color: 'var(--color-ink)', margin: '4px 0 0', lineHeight: 1.09 }}>
            Workspace Settings
          </h1>
        </div>

        {loading ? (
          <div style={{ padding: 'var(--spacing-48) 0', textAlign: 'center', color: 'var(--color-ash)' }}>
            Loading settings configurations...
          </div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: '240px 1fr', gap: 'var(--spacing-32)', alignItems: 'flex-start' }}>
            
            {/* Sidebar Navigation */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => setActiveTab(tab.id)}
                  style={{
                    textAlign: 'left',
                    padding: '10px 16px',
                    fontSize: '13.5px',
                    fontWeight: activeTab === tab.id ? 600 : 400,
                    borderRadius: '10px',
                    background: activeTab === tab.id ? 'var(--color-fog)' : 'transparent',
                    color: activeTab === tab.id ? 'var(--color-ink)' : 'var(--color-ash)',
                    border: 'none',
                    cursor: 'pointer',
                    transition: 'all 0.15s ease'
                  }}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            {/* Config Panels */}
            <div style={{ minWidth: 0 }}>
              
              {/* Profile Config */}
              {activeTab === 'profile' && (
                <SteepCard>
                  <h2 style={{ fontSize: 'var(--text-body-lg)', fontWeight: 500, margin: '0 0 20px', color: 'var(--color-ink)' }}>
                    Company Profile
                  </h2>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                    <SteepInput
                      id="profile-name"
                      label="Organization Name"
                      value={company?.name || 'SmartOnboard Partner'}
                      readOnly
                      disabled
                    />
                    <SteepInput
                      id="profile-domain"
                      label="Workspace Domain"
                      value={company?.slug ? `${company.slug}.com` : 'smartonboard.io'}
                      readOnly
                      disabled
                    />
                    <SteepInput
                      id="profile-industry"
                      label="Industry"
                      value="Technology"
                      readOnly
                      disabled
                    />
                    <SteepInput
                      id="profile-size"
                      label="Company Size"
                      value="50-100 Employees"
                      readOnly
                      disabled
                    />
                  </div>
                </SteepCard>
              )}

              {/* Recruiters List */}
              {activeTab === 'recruiters' && (
                <SteepCard>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
                    <h2 style={{ fontSize: 'var(--text-body-lg)', fontWeight: 500, margin: 0, color: 'var(--color-ink)' }}>
                      Active Recruiter Team
                    </h2>
                    <SteepButton variant="secondary" size="sm">Invite Teammate</SteepButton>
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 16px', background: 'var(--color-fog)', borderRadius: '12px', border: '1px solid var(--border)' }}>
                      <div>
                        <strong style={{ fontSize: '13.5px', color: 'var(--color-ink)' }}>Sarah Recruiter</strong>
                        <span style={{ display: 'block', fontSize: '11px', color: 'var(--color-ash)', marginTop: '2px' }}>sarah@company.com</span>
                      </div>
                      <SteepBadge variant="success">Workspace Owner</SteepBadge>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 16px', background: 'var(--color-fog)', borderRadius: '12px', border: '1px solid var(--border)' }}>
                      <div>
                        <strong style={{ fontSize: '13.5px', color: 'var(--color-ink)' }}>John Recruiter</strong>
                        <span style={{ display: 'block', fontSize: '11px', color: 'var(--color-ash)', marginTop: '2px' }}>john.rec@company.com</span>
                      </div>
                      <SteepBadge variant="neutral">Recruiter</SteepBadge>
                    </div>
                  </div>
                </SteepCard>
              )}

              {/* Security Tab */}
              {activeTab === 'security' && (
                <SteepCard>
                  <h2 style={{ fontSize: 'var(--text-body-lg)', fontWeight: 500, margin: '0 0 12px', color: 'var(--color-ink)' }}>
                    SSO & Access Rules
                  </h2>
                  <p style={{ fontSize: 'var(--text-caption)', color: 'var(--color-ash)', marginBottom: 20 }}>
                    Manage sign-in options, restrict login networks, and control enterprise security policy.
                  </p>
                  
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                    <div style={{ padding: '16px', border: '1px solid var(--border)', borderRadius: '12px', background: 'var(--color-fog)' }}>
                      <div style={{ fontWeight: 600, fontSize: '13.5px', marginBottom: '4px' }}>Google Workspace Single Sign-On (SSO)</div>
                      <div style={{ fontSize: '12px', color: 'var(--color-ash)' }}>Enforce corporate Google Workspace log in for all recruiter accounts matching the verified domain.</div>
                      <SteepButton variant="secondary" size="sm" style={{ marginTop: '12px' }}>Enable SSO enforcement</SteepButton>
                    </div>

                    <div style={{ padding: '16px', border: '1px solid var(--border)', borderRadius: '12px', background: 'var(--color-fog)' }}>
                      <div style={{ fontWeight: 600, fontSize: '13.5px', marginBottom: '4px' }}>IP Access Whitelist Restrictions</div>
                      <div style={{ fontSize: '12px', color: 'var(--color-ash)' }}>Restrict workspace logins only to corporate networks and office IP ranges.</div>
                      <SteepButton variant="secondary" size="sm" style={{ marginTop: '12px' }}>Configure Whitelisted IP ranges</SteepButton>
                    </div>
                  </div>
                </SteepCard>
              )}

              {/* Notifications Tab */}
              {activeTab === 'notifications' && (
                <SteepCard>
                  <h2 style={{ fontSize: 'var(--text-body-lg)', fontWeight: 500, margin: '0 0 12px', color: 'var(--color-ink)' }}>
                    Email Notifications
                  </h2>
                  <p style={{ fontSize: 'var(--text-caption)', color: 'var(--color-ash)', marginBottom: 20 }}>
                    Select system alerts and updates you wish to receive in your inbox.
                  </p>
                  
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                    <label style={{ display: 'flex', gap: '10px', alignItems: 'center', fontSize: '13.5px', cursor: 'pointer' }}>
                      <input type="checkbox" checked={notifAppReceived} onChange={e => setNotifAppReceived(e.target.checked)} />
                      <span>New application received</span>
                    </label>
                    <label style={{ display: 'flex', gap: '10px', alignItems: 'center', fontSize: '13.5px', cursor: 'pointer' }}>
                      <input type="checkbox" checked={notifParsingDone} onChange={e => setNotifParsingDone(e.target.checked)} />
                      <span>Resume processing completed</span>
                    </label>
                    <label style={{ display: 'flex', gap: '10px', alignItems: 'center', fontSize: '13.5px', cursor: 'pointer' }}>
                      <input type="checkbox" checked={notifInterviewAccepted} onChange={e => setNotifInterviewAccepted(e.target.checked)} />
                      <span>Interview accepted by candidate</span>
                    </label>
                    <label style={{ display: 'flex', gap: '10px', alignItems: 'center', fontSize: '13.5px', cursor: 'pointer' }}>
                      <input type="checkbox" checked={notifWithdrawn} onChange={e => setNotifWithdrawn(e.target.checked)} />
                      <span>Candidate withdrew application</span>
                    </label>
                    <label style={{ display: 'flex', gap: '10px', alignItems: 'center', fontSize: '13.5px', cursor: 'pointer' }}>
                      <input type="checkbox" checked={notifVerifyFail} onChange={e => setNotifVerifyFail(e.target.checked)} />
                      <span>Candidate verification checks failed</span>
                    </label>
                  </div>
                </SteepCard>
              )}

              {/* Verification Tab */}
              {activeTab === 'verification' && (
                <SteepCard>
                  <h2 style={{ fontSize: 'var(--text-body-lg)', fontWeight: 500, margin: '0 0 16px', color: 'var(--color-ink)' }}>
                    MX / DNS Domain Verification
                  </h2>
                  <p style={{ fontSize: 'var(--text-caption)', color: 'var(--color-ash)', lineHeight: 1.33, margin: '0 0 16px' }}>
                    Verify company email domain records to secure workspace operations and candidate communication channels.
                  </p>
                  <div style={{
                    border: '1px solid var(--border)',
                    borderRadius: '16px',
                    padding: 16,
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    background: 'var(--color-fog)'
                  }}>
                    <div>
                      <div style={{ fontSize: 14, fontWeight: 600 }}>MX Domain State: <span style={{ color: company?.domain_verified ? 'var(--color-success)' : 'var(--color-rust)' }}>{company?.domain_verified ? 'Verified & Active' : 'Pending Verification'}</span></div>
                      <div style={{ fontSize: 11, color: 'var(--color-ash)', marginTop: 4 }}>Expected MX domain record: mail.{company?.slug ? `${company.slug}.com` : 'smartonboard.io'}</div>
                    </div>
                    {!company?.domain_verified && (
                      <SteepButton variant="secondary" size="sm" onClick={() => alert('Checking records...')}>
                        Verify Records
                      </SteepButton>
                    )}
                  </div>
                </SteepCard>
              )}

              {/* Billing Tab */}
              {activeTab === 'billing' && (
                <SteepCard>
                  <h2 style={{ fontSize: 'var(--text-body-lg)', fontWeight: 500, margin: '0 0 12px', color: 'var(--color-ink)' }}>
                    Subscription & Billing
                  </h2>
                  <div style={{
                    fontSize: 10,
                    fontWeight: 600,
                    color: 'var(--color-rust)',
                    letterSpacing: '0.05em',
                    textTransform: 'uppercase',
                    marginBottom: 12
                  }}>
                    Standard Employer Plan
                  </div>
                  <p style={{ fontSize: 13.5, lineHeight: 1.35, color: 'var(--color-ash)', margin: 0 }}>
                    SmartOnboard platform subscription plans are calculated per active job posting. 
                  </p>
                  <div style={{ borderTop: '1px solid var(--border)', marginTop: 16, paddingTop: 16, fontSize: 13, color: 'var(--color-ink)', fontWeight: 500 }}>
                    Workspace Plan Rates: <strong style={{ color: 'var(--color-rust)' }}>$49/month per active job</strong>
                  </div>
                </SteepCard>
              )}

            </div>

          </div>
        )}
      </div>
    </AppLayout>
  )
}
