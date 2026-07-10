import { useState } from 'react'
import TalentPoolDashboard from './TalentPoolDashboard'
import TalentPools from './TalentPools'
import TalentSearch from './TalentSearch'
import CandidateRelationshipDrawer from './CandidateRelationshipDrawer'

type CRMTab = 'dashboard' | 'pools' | 'search' | 'followups'

export default function TalentCRM() {
  const [activeTab, setActiveTab] = useState<CRMTab>('dashboard')
  const [selectedCandidateId, setSelectedCandidateId] = useState<string | null>(null)
  const [isDrawerOpen, setIsDrawerOpen] = useState(false)
  const selectedJobId = '74b162a7-a3dc-4337-a275-789be4674756' // Default demo job id from seed

  const handleOpenCandidate = (candidateId: string) => {
    setSelectedCandidateId(candidateId)
    setIsDrawerOpen(true)
  }

  const renderActiveContent = () => {
    switch (activeTab) {
      case 'dashboard':
        return <TalentPoolDashboard onSelectCandidate={handleOpenCandidate} />
      case 'pools':
        return <TalentPools onSelectCandidate={handleOpenCandidate} />
      case 'search':
        return <TalentSearch onSelectCandidate={handleOpenCandidate} />
      case 'followups':
        return (
          <div style={{ padding: '24px', background: 'var(--bg-card)', borderRadius: '12px', border: '1px solid var(--border)' }}>
            <h3 style={{ margin: '0 0 8px 0', fontSize: '18px', fontWeight: 700 }}>Follow-up Reminders</h3>
            <p style={{ margin: '0 0 20px 0', fontSize: '13.5px', color: 'var(--text-secondary)' }}>
              Candidates scheduled for outreach contact in the next 14 days
            </p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {[
                { name: 'Marcus Wright', date: 'Tomorrow', stage: 'Attempting Contact', status: 'Warm Lead' },
                { name: 'Kyle Reese', date: 'In 3 days', stage: 'Conversation Started', status: 'Interested' },
                { name: 'Kate Brewster', date: 'In 5 days', stage: 'Talent Pool', status: 'Silver Medalist' }
              ].map((item, idx) => (
                <div
                  key={idx}
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    padding: '16px',
                    borderRadius: '8px',
                    border: '1px solid var(--border)',
                    background: 'var(--bg)'
                  }}
                >
                  <div>
                    <h5 style={{ margin: 0, fontSize: '14px', fontWeight: 650 }}>{item.name}</h5>
                    <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                      Stage: {item.stage} • {item.status}
                    </span>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <span style={{ fontSize: '12.5px', fontWeight: 700, color: 'var(--accent)' }}>
                      {item.date}
                    </span>
                    <button
                      type="button"
                      className="btn btn--outline"
                      style={{ display: 'block', marginTop: '4px', fontSize: '11px', padding: '4px 8px', borderRadius: '4px' }}
                      onClick={() => handleOpenCandidate('ff8ad11b-f3c2-414c-bf3c-51fb5743d0a3')} // Demo Candidate
                    >
                      Open CRM Card
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )
      default:
        return null
    }
  }

  return (
    <div
      style={{
        display: 'flex',
        minHeight: 'calc(100vh - var(--header-h))',
        background: 'var(--bg)',
        fontFamily: 'var(--font-sans, sans-serif)',
        color: 'var(--text)'
      }}
    >
      {/* Local CRM Navigation Sidebar */}
      <div
        style={{
          width: '220px',
          borderRight: '1px solid var(--border)',
          background: 'var(--bg-card)',
          padding: '24px 16px',
          display: 'flex',
          flexDirection: 'column',
          gap: '24px'
        }}
      >
        <div>
          <h3 style={{ margin: 0, fontSize: '16px', fontWeight: 700, letterSpacing: '-0.02em' }}>
            Talent CRM
          </h3>
          <span style={{ fontSize: '11px', color: 'var(--text-tertiary)', textTransform: 'uppercase', fontWeight: 700 }}>
            AI-first Sourcing
          </span>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
          {(
            [
              { id: 'dashboard', label: 'CRM Dashboard', icon: '📊' },
              { id: 'pools', label: 'Talent Pools', icon: '📁' },
              { id: 'search', label: 'NL Search', icon: '🔎' },
              { id: 'followups', label: 'Follow-ups', icon: '⏰' }
            ] as const
          ).map((tab) => (
            <button
              key={tab.id}
              type="button"
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '10px',
                padding: '10px 14px',
                borderRadius: '8px',
                fontSize: '13px',
                fontWeight: activeTab === tab.id ? 700 : 550,
                color: activeTab === tab.id ? 'var(--accent)' : 'var(--text-secondary)',
                background: activeTab === tab.id ? 'var(--accent-subtle, #eff6ff)' : 'transparent',
                border: 'none',
                textAlign: 'left',
                cursor: 'pointer',
                transition: 'all 0.15s ease'
              }}
              onClick={() => setActiveTab(tab.id)}
            >
              <span>{tab.icon}</span>
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Main Content Area */}
      <div style={{ flex: 1, padding: '32px', overflowY: 'auto' }}>
        {renderActiveContent()}
      </div>

      {/* Slideout Candidate CRM Details Drawer */}
      {isDrawerOpen && selectedCandidateId && (
        <CandidateRelationshipDrawer
          candidateId={selectedCandidateId}
          jobId={selectedJobId}
          onClose={() => setIsDrawerOpen(false)}
        />
      )}
    </div>
  )
}
