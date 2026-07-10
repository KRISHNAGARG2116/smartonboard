

interface TalentPoolDashboardProps {
  onSelectCandidate: (id: string) => void
}

export default function TalentPoolDashboard({ onSelectCandidate }: TalentPoolDashboardProps) {
  // Mock analytics dataset based on product specifications
  const metrics = [
    { label: 'Pool → Interview', value: '38%', trend: '+4.2% MoM' },
    { label: 'Pool → Offer', value: '18%', trend: '+2.1% MoM' },
    { label: 'Pool → Hire', value: '12%', trend: '+0.8% MoM' },
    { label: 'Avg Days in Pool', value: '42 days', trend: '-3 days MoM' }
  ]

  const matchAnalytics = [
    { label: 'Avg AI Match Score', value: '82%' },
    { label: 'Avg Hire Match Score', value: '92%' },
    { label: 'Avg Reject Match Score', value: '64%' },
    { label: 'Recruiter Override Rate', value: '14.2%' },
    { label: 'AI Helpfulness Rate (👍)', value: '88.5%' },
    { label: 'Candidate Rediscovery Rate', value: '26.8%' }
  ]

  const leaderboard = [
    { name: 'Sarah Connor', outreach: 142, responseRate: '68%' },
    { name: 'John Connor', outreach: 98, responseRate: '72%' },
    { name: 'T-800', outreach: 85, responseRate: '54%' }
  ]

  const activeLeads = [
    { id: 'ff8ad11b-f3c2-414c-bf3c-51fb5743d0a3', name: 'John Doe', stage: 'Conversation Started', match: 92, owner: 'Sarah Connor', activity: 'E-mail opened 2h ago' },
    { id: 'lead-2', name: 'Marcus Wright', stage: 'Attempting Contact', match: 86, owner: 'John Connor', activity: 'Added to React Pool 1d ago' },
    { id: 'lead-3', name: 'Kyle Reese', stage: 'Interested', match: 74, owner: 'Sarah Connor', activity: 'Replied to sequence 4h ago' }
  ]

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '32px' }}>
      {/* Page Title */}
      <div>
        <h2 style={{ margin: 0, fontSize: '24px', fontWeight: 800, letterSpacing: '-0.03em' }}>
          CRM Analytics & Dashboard
        </h2>
        <p style={{ margin: '4px 0 0 0', fontSize: '14px', color: 'var(--text-secondary)' }}>
          Overview of sourcing conversion metrics and match intelligence performance
        </p>
      </div>

      {/* Metric Cards Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '20px' }}>
        {metrics.map((card, idx) => (
          <div
            key={idx}
            style={{
              background: 'var(--bg-card)',
              border: '1px solid var(--border)',
              borderRadius: '12px',
              padding: '20px',
              boxShadow: 'var(--shadow-premium, 0 4px 20px -6px rgba(0,0,0,0.02))'
            }}
          >
            <span style={{ fontSize: '12px', color: 'var(--text-secondary)', textTransform: 'uppercase', fontWeight: 700 }}>
              {card.label}
            </span>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px', marginTop: '8px' }}>
              <span style={{ fontSize: '28px', fontWeight: 800, letterSpacing: '-0.02em' }}>{card.value}</span>
              <span style={{ fontSize: '11px', color: card.trend.startsWith('+') || card.trend.startsWith('-3') ? '#10b981' : '#f59e0b', fontWeight: 700 }}>
                {card.trend}
              </span>
            </div>
          </div>
        ))}
      </div>

      {/* Main Grid: CRM Leads and Match Analytics */}
      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '24px' }}>
        {/* Active CRM Leads Table */}
        <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: '12px', padding: '24px' }}>
          <h3 style={{ margin: '0 0 16px 0', fontSize: '16px', fontWeight: 700 }}>Active CRM Leads</h3>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13.5px' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border)', textAlign: 'left', color: 'var(--text-secondary)' }}>
                  <th style={{ padding: '12px 8px', fontWeight: 650 }}>Name</th>
                  <th style={{ padding: '12px 8px', fontWeight: 650 }}>CRM Stage</th>
                  <th style={{ padding: '12px 8px', fontWeight: 650 }}>Match Score</th>
                  <th style={{ padding: '12px 8px', fontWeight: 650 }}>Owner</th>
                  <th style={{ padding: '12px 8px', fontWeight: 650 }}>Recent Activity</th>
                  <th style={{ padding: '12px 8px', fontWeight: 650, textAlign: 'right' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {activeLeads.map((lead) => (
                  <tr key={lead.id} style={{ borderBottom: '1px solid var(--border-subtle, #f3f4f6)' }}>
                    <td style={{ padding: '16px 8px', fontWeight: 600 }}>{lead.name}</td>
                    <td style={{ padding: '16px 8px' }}>
                      <span style={{ background: 'var(--accent-subtle)', color: 'var(--accent)', padding: '2px 8px', borderRadius: '4px', fontSize: '11px', fontWeight: 700 }}>
                        {lead.stage}
                      </span>
                    </td>
                    <td style={{ padding: '16px 8px', fontWeight: 700, color: lead.match >= 90 ? '#10b981' : lead.match >= 75 ? '#3b82f6' : '#f59e0b' }}>
                      {lead.match}%
                    </td>
                    <td style={{ padding: '16px 8px', color: 'var(--text-secondary)' }}>{lead.owner}</td>
                    <td style={{ padding: '16px 8px', color: 'var(--text-tertiary)', fontSize: '12.5px' }}>{lead.activity}</td>
                    <td style={{ padding: '16px 8px', textAlign: 'right' }}>
                      <button
                        type="button"
                        className="btn btn--link"
                        style={{ padding: 0, fontSize: '13px', fontWeight: 700 }}
                        onClick={() => onSelectCandidate(lead.id)}
                      >
                        Manage
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* AI Match Model Internal Performance Metrics */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: '12px', padding: '24px' }}>
            <h3 style={{ margin: '0 0 16px 0', fontSize: '16px', fontWeight: 700 }}>AI Match Accuracy</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {matchAnalytics.map((stat, idx) => (
                <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>{stat.label}</span>
                  <span style={{ fontSize: '14px', fontWeight: 700 }}>{stat.value}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Outreach Leaderboard */}
          <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: '12px', padding: '24px' }}>
            <h3 style={{ margin: '0 0 16px 0', fontSize: '16px', fontWeight: 700 }}>Recruiter Outreach Leaderboard</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {leaderboard.map((user, idx) => (
                <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>{idx + 1}.</span>
                    <span style={{ fontSize: '13.5px', fontWeight: 650 }}>{user.name}</span>
                  </div>
                  <span style={{ fontSize: '12.5px', color: 'var(--text-secondary)' }}>
                    {user.outreach} sent • <strong>{user.responseRate}</strong> reply
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
