import { useState } from 'react'
import AppLayout from '../../components/AppLayout'

interface SecurityMetric {
  name: string
  status: boolean
  impact: string
}

interface IncidentEvent {
  id: string
  severity: 'Informational' | 'Low' | 'Medium' | 'High' | 'Critical'
  user: string
  integration: string
  event_type: string
  time: string
  details: string
}

export default function SecurityDashboard() {
  const [severityFilter, setSeverityFilter] = useState('All')
  const [searchQuery, setSearchQuery] = useState('')

  const scoreFactors: SecurityMetric[] = [
    { name: 'MFA Enforced', status: true, impact: 'High' },
    { name: 'SSO Configured', status: true, impact: 'Medium' },
    { name: 'SCIM Directory Sync Active', status: true, impact: 'Medium' },
    { name: 'Secrets Envelopes Rotated', status: true, impact: 'High' },
    { name: 'Database Backups Verified', status: true, impact: 'Critical' },
    { name: 'No Open Critical Alerts', status: true, impact: 'Critical' },
    { name: 'Data Retention Policies Compliant', status: false, impact: 'Medium' }
  ]

  const incidents: IncidentEvent[] = [
    {
      id: 'sec-819',
      severity: 'Critical',
      user: 'System lock',
      integration: 'Auth System',
      event_type: 'Brute Force Attempt Blocked',
      time: '10 mins ago',
      details: 'IP 182.16.82.9 locked out after 5 consecutive failed login attempts.'
    },
    {
      id: 'sec-815',
      severity: 'High',
      user: 'sarah.k@corp.com',
      integration: 'Recruiter Admin Console',
      event_type: 'Privilege Escalation Warning',
      time: '1 hr ago',
      details: 'Attempted to purge historical security audit logs. Bypass block executed.'
    },
    {
      id: 'sec-802',
      severity: 'Medium',
      user: 'Google Workspace Sync',
      integration: 'SCIM Connector',
      event_type: 'User Sync Complete',
      time: '4 hrs ago',
      details: 'Synchronized 14 users and soft-deprovisioned 1 inactive recruiter.'
    },
    {
      id: 'sec-798',
      severity: 'Informational',
      user: 'alex.recruiter@corp.com',
      integration: 'Candidate Exporter',
      event_type: 'Export Logged',
      time: '6 hrs ago',
      details: 'Exported 12 candidate records containing resumes to csv.'
    }
  ]

  const filteredIncidents = incidents.filter(evt => {
    const matchesSeverity = severityFilter === 'All' || evt.severity === severityFilter
    const matchesSearch =
      evt.user.toLowerCase().includes(searchQuery.toLowerCase()) ||
      evt.event_type.toLowerCase().includes(searchQuery.toLowerCase()) ||
      evt.details.toLowerCase().includes(searchQuery.toLowerCase())
    return matchesSeverity && matchesSearch
  })

  // Calculate score based on completed factors
  const completedCount = scoreFactors.filter(f => f.status).length
  const totalScore = Math.round((completedCount / scoreFactors.length) * 100)

  return (
    <AppLayout>
      <div
        style={{
          fontFamily: 'var(--font-sans, sans-serif)',
          color: 'var(--text)',
          padding: '24px',
          display: 'flex',
          flexDirection: 'column',
          gap: '24px'
        }}
      >
        <div>
          <h1 style={{ margin: 0, fontSize: '24px', fontWeight: 800 }}>Tenant Security Dashboard</h1>
          <span style={{ fontSize: '12.5px', color: 'var(--text-secondary)' }}>
            Real-time security posture assessment, compliance benchmarks, and network event monitoring.
          </span>
        </div>

        {/* Posture Score Breakdown */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '24px' }}>
          {/* Posture Dial Card */}
          <div
            style={{
              background: 'var(--bg-card)',
              border: '1px solid var(--border)',
              borderRadius: '12px',
              padding: '24px',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '12px'
            }}
          >
            <span style={{ fontSize: '13px', fontWeight: 700, color: 'var(--text-secondary)' }}>
              Overall Security Score
            </span>
            <div style={{ position: 'relative', display: 'inline-flex' }}>
              <div
                style={{
                  width: '120px',
                  height: '120px',
                  borderRadius: '50%',
                  border: '10px solid #10b981',
                  borderTopColor: '#f3f4f6',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center'
                }}
              >
                <span style={{ fontSize: '28px', fontWeight: 900 }}>{totalScore}%</span>
              </div>
            </div>
            <span style={{ fontSize: '12.5px', background: '#eff6ff', color: 'var(--accent)', padding: '4px 8px', borderRadius: '4px', fontWeight: 650 }}>
              ✓ Highly Compliant
            </span>
          </div>

          {/* Checklist details */}
          <div
            style={{
              background: 'var(--bg-card)',
              border: '1px solid var(--border)',
              borderRadius: '12px',
              padding: '20px'
            }}
          >
            <h3 style={{ margin: '0 0 16px 0', fontSize: '16px', fontWeight: 700 }}>Security Score Breakdown</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {scoreFactors.map((factor, idx) => (
                <div
                  key={idx}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '8px 12px',
                    borderBottom: '1px solid var(--border-subtle, #f3f4f6)',
                    fontSize: '13.5px'
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span>{factor.status ? '🟢' : '🔴'}</span>
                    <span style={{ fontWeight: 600 }}>{factor.name}</span>
                  </div>
                  <span style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
                    Impact: {factor.impact}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Security Timeline Filter and list */}
        <div
          style={{
            background: 'var(--bg-card)',
            border: '1px solid var(--border)',
            borderRadius: '12px',
            padding: '20px'
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', gap: '12px' }}>
            <h3 style={{ margin: 0, fontSize: '16px', fontWeight: 700 }}>Security Incident Timeline</h3>
            
            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
              <input
                type="text"
                placeholder="Search events..."
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                style={{
                  padding: '6px 12px',
                  borderRadius: '6px',
                  border: '1px solid var(--border)',
                  fontSize: '13px'
                }}
              />
              <select
                value={severityFilter}
                onChange={e => setSeverityFilter(e.target.value)}
                style={{
                  padding: '6px 12px',
                  borderRadius: '6px',
                  border: '1px solid var(--border)',
                  fontSize: '13px'
                }}
              >
                <option value="All">All Severities</option>
                <option value="Informational">Informational</option>
                <option value="Low">Low</option>
                <option value="Medium">Medium</option>
                <option value="High">High</option>
                <option value="Critical">Critical</option>
              </select>
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {filteredIncidents.map(evt => (
              <div
                key={evt.id}
                style={{
                  border: '1px solid var(--border)',
                  borderRadius: '8px',
                  padding: '12px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '6px',
                  fontSize: '13px'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span
                      style={{
                        padding: '2px 6px',
                        borderRadius: '4px',
                        fontSize: '10px',
                        fontWeight: 700,
                        color: '#ffffff',
                        background:
                          evt.severity === 'Critical' ? '#ef4444' :
                          evt.severity === 'High' ? '#f97316' :
                          evt.severity === 'Medium' ? '#f59e0b' : '#3b82f6'
                      }}
                    >
                      {evt.severity}
                    </span>
                    <strong style={{ fontSize: '13.5px' }}>{evt.event_type}</strong>
                  </div>
                  <span style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>{evt.time}</span>
                </div>
                <p style={{ margin: 0, color: 'var(--text-secondary)' }}>{evt.details}</p>
                <div style={{ display: 'flex', gap: '16px', fontSize: '11.5px', color: 'var(--accent)' }}>
                  <span>Actor: {evt.user}</span>
                  <span>System: {evt.integration}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </AppLayout>
  )
}
