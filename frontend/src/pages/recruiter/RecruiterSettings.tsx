import { useState, useEffect } from 'react'
import AppLayout from '../../components/AppLayout'
import { fetchCompany, type Company } from '../../api'
import SteepCard from '../../components/design-system/SteepCard'
import SteepButton from '../../components/design-system/SteepButton'
import SteepInput from '../../components/design-system/SteepInput'
import SteepBadge from '../../components/design-system/SteepBadge'

type SettingsTab = 'profile' | 'branding' | 'recruiters' | 'integrations' | 'security' | 'notifications' | 'ai' | 'verification'

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

  // Branding States
  const [brandColor, setBrandColor] = useState('#17191c')
  const [logoUrl, setLogoUrl] = useState('')

  // Integration States
  const [smtpHost, setSmtpHost] = useState('smtp.mailtrap.io')
  const [smtpPort, setSmtpPort] = useState('2525')
  const [smtpUser, setSmtpUser] = useState('work_smtp_user')
  const [calendarSync, setCalendarSync] = useState(true)

  // Security SSO & Break Glass States
  const [ssoEnabled, setSsoEnabled] = useState(false)
  const [idpEntityId, setIdpEntityId] = useState('https://idp.okta.com/exk1234')
  const [idpSsoUrl, setIdpSsoUrl] = useState('https://idp.okta.com/exk1234/sso')
  const [emergencyBypass, setEmergencyBypass] = useState(false)

  // AI preferences
  const [aiTone, setAiTone] = useState('professional')
  const [aiAutoRank, setAiAutoRank] = useState(true)

  useEffect(() => {
    setLoading(true)
    fetchCompany()
      .then(co => setCompany(co))
      .catch(err => console.error('Error fetching company details:', err))
      .finally(() => setLoading(false))
  }, [])

  const tabs: { id: SettingsTab; label: string }[] = [
    { id: 'profile', label: 'Company Profile' },
    { id: 'branding', label: 'Branding & Logo' },
    { id: 'recruiters', label: 'Recruiters List' },
    { id: 'integrations', label: 'Email & Calendar' },
    { id: 'security', label: 'Security & SSO' },
    { id: 'notifications', label: 'Notifications' },
    { id: 'ai', label: 'AI Preferences' },
    { id: 'verification', label: 'DNS Verification' },
  ]

  const handleSaveSettings = () => {
    alert('Settings configuration saved successfully!')
  }

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

              {/* Branding Configuration */}
              {activeTab === 'branding' && (
                <SteepCard>
                  <h2 style={{ fontSize: 'var(--text-body-lg)', fontWeight: 500, margin: '0 0 20px', color: 'var(--color-ink)' }}>
                    Organization Branding
                  </h2>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                    <div style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
                      <div style={{ width: 64, height: 64, borderRadius: 8, background: brandColor, display: 'grid', placeItems: 'center', color: '#fff', fontSize: '24px' }}>
                        🏢
                      </div>
                      <div>
                        <span style={{ fontSize: '13px', fontWeight: 650, display: 'block' }}>Primary Brand Color</span>
                        <input
                          type="color"
                          value={brandColor}
                          onChange={e => setBrandColor(e.target.value)}
                          style={{ border: 'none', background: 'none', padding: 0, height: 36, width: 80, cursor: 'pointer' }}
                        />
                      </div>
                    </div>
                    <SteepInput
                      id="logo-url"
                      label="Custom Logo URL"
                      placeholder="https://company.com/logo.png"
                      value={logoUrl}
                      onChange={e => setLogoUrl(e.target.value)}
                    />
                    <SteepButton onClick={handleSaveSettings} style={{ alignSelf: 'flex-start', marginTop: 12 }}>
                      Save Branding
                    </SteepButton>
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
                    <SteepButton variant="secondary" size="sm" onClick={() => alert('Invitation sent to developer@smartonboard.io')}>
                      Invite Teammate
                    </SteepButton>
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

              {/* Email & Calendar Integrations */}
              {activeTab === 'integrations' && (
                <SteepCard>
                  <h2 style={{ fontSize: 'var(--text-body-lg)', fontWeight: 500, margin: '0 0 20px', color: 'var(--color-ink)' }}>
                    Email & Calendar Settings
                  </h2>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
                    {/* SMTP */}
                    <div style={{ borderBottom: '1px solid var(--border-subtle)', paddingBottom: 16 }}>
                      <span style={{ fontSize: '12px', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-secondary)' }}>SMTP Configuration</span>
                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 80px', gap: 12, marginTop: 12 }}>
                        <SteepInput id="smtp-host" label="Outgoing Mail Server (SMTP)" value={smtpHost} onChange={e => setSmtpHost(e.target.value)} />
                        <SteepInput id="smtp-port" label="Port" value={smtpPort} onChange={e => setSmtpPort(e.target.value)} />
                      </div>
                      <SteepInput id="smtp-user" label="SMTP Username" value={smtpUser} onChange={e => setSmtpUser(e.target.value)} style={{ marginTop: 12 }} />
                    </div>
                    {/* Calendar Availability */}
                    <div>
                      <span style={{ fontSize: '12px', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-secondary)' }}>Calendar Sync</span>
                      <label style={{ display: 'flex', gap: 10, alignItems: 'center', fontSize: '13.5px', cursor: 'pointer', marginTop: 12 }}>
                        <input type="checkbox" checked={calendarSync} onChange={e => setCalendarSync(e.target.checked)} />
                        <span>Synchronize availability with Google Calendar</span>
                      </label>
                    </div>
                    <SteepButton onClick={handleSaveSettings} style={{ alignSelf: 'flex-start' }}>
                      Save Integration Settings
                    </SteepButton>
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
                    Manage SAML SSO configurations, dynamic certificate rotations, and emergency recovery access.
                  </p>
                  
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                    <div style={{ padding: '16px', border: '1px solid var(--border)', borderRadius: '12px', background: 'var(--color-fog)' }}>
                      <label style={{ display: 'flex', gap: 10, alignItems: 'center', fontSize: '13.5px', cursor: 'pointer', marginBottom: 12 }}>
                        <input type="checkbox" checked={ssoEnabled} onChange={e => setSsoEnabled(e.target.checked)} />
                        <strong>Enable SAML Single Sign-On (SSO)</strong>
                      </label>
                      {ssoEnabled && (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 12, marginTop: 12 }}>
                          <SteepInput id="sso-entity-id" label="IdP Entity ID" value={idpEntityId} onChange={e => setIdpEntityId(e.target.value)} />
                          <SteepInput id="sso-url" label="IdP Login URL" value={idpSsoUrl} onChange={e => setIdpSsoUrl(e.target.value)} />
                        </div>
                      )}
                    </div>

                    <div style={{ padding: '16px', border: '1px solid var(--border)', borderRadius: '12px', background: 'var(--color-fog)' }}>
                      <label style={{ display: 'flex', gap: 10, alignItems: 'center', fontSize: '13.5px', cursor: 'pointer', marginBottom: 12 }}>
                        <input type="checkbox" checked={emergencyBypass} onChange={e => setEmergencyBypass(e.target.checked)} />
                        <strong>Enable Local "Break-Glass" Emergency Bypass Login</strong>
                      </label>
                      <div style={{ fontSize: '11.5px', color: 'var(--color-ash)' }}>
                        Allows designated owner accounts to log in using local credentials if the external SSO provider is offline.
                      </div>
                    </div>

                    <SteepButton onClick={handleSaveSettings} style={{ alignSelf: 'flex-start' }}>
                      Save Security Rules
                    </SteepButton>
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
                    <SteepButton onClick={handleSaveSettings} style={{ alignSelf: 'flex-start', marginTop: 12 }}>
                      Save Preferences
                    </SteepButton>
                  </div>
                </SteepCard>
              )}

              {/* AI Settings Tab */}
              {activeTab === 'ai' && (
                <SteepCard>
                  <h2 style={{ fontSize: 'var(--text-body-lg)', fontWeight: 500, margin: '0 0 20px', color: 'var(--color-ink)' }}>
                    AI Recruiting Agent Settings
                  </h2>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                    <div>
                      <label style={{ fontSize: '12px', fontWeight: 700, display: 'block', color: 'var(--text-secondary)', marginBottom: 6 }}>Evaluation summary style</label>
                      <select value={aiTone} onChange={e => setAiTone(e.target.value)} style={{ padding: '8px 12px', borderRadius: 8, border: '1px solid var(--border)', fontSize: '13.5px', width: '100%' }}>
                        <option value="professional">Professional / Concise</option>
                        <option value="detailed">Exhaustive / Risk-focused</option>
                        <option value="bullet">Bullet Points Only</option>
                      </select>
                    </div>

                    <label style={{ display: 'flex', gap: '10px', alignItems: 'center', fontSize: '13.5px', cursor: 'pointer', marginTop: 8 }}>
                      <input type="checkbox" checked={aiAutoRank} onChange={e => setAiAutoRank(e.target.checked)} />
                      <strong>Auto-rank incoming candidate applicability</strong>
                    </label>

                    <SteepButton onClick={handleSaveSettings} style={{ alignSelf: 'flex-start', marginTop: 12 }}>
                      Save AI Preferences
                    </SteepButton>
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

            </div>

          </div>
        )}
      </div>
    </AppLayout>
  )
}
