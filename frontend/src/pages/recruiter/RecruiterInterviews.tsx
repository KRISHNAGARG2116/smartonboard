import { useState, useEffect } from 'react'
import AppLayout from '../../components/AppLayout'
import { fetchApplications, type Application } from '../../api'

export default function RecruiterInterviews() {
  const [applications, setApplications] = useState<Application[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchApplications()
      .then(apps => setApplications(apps))
      .catch(err => console.error('Error fetching applications:', err))
      .finally(() => setLoading(false))
  }, [])

  // Filter applications with scheduled interviews
  // (In the model, application has a slot/interview structure or status)
  const interviewApps = applications.filter(
    app => app.status === 'interview' || app.status === 'screening'
  )

  return (
    <AppLayout>
      <div className="container" style={{ padding: 'var(--space-6) 0 var(--space-12)' }}>
        {/* Header */}
        <div style={{
          borderBottom: '1px solid var(--border)',
          paddingBottom: 'var(--space-6)',
          marginBottom: 'var(--space-6)'
        }}>
          <span style={{ fontSize: 10, fontWeight: 500, color: 'var(--text-secondary)', letterSpacing: '0.05em', textTransform: 'uppercase' }}>
            Talent Coordination
          </span>
          <h1 style={{ fontSize: '29px', fontWeight: 500, letterSpacing: '-0.02em', color: 'var(--text)', margin: '4px 0 0', lineHeight: 1.09 }}>
            Interviews Calendar
          </h1>
        </div>

        {loading ? (
          <div style={{ padding: 'var(--space-12) 0', textAlign: 'center', color: 'var(--text-secondary)' }}>
            Loading interview calendar...
          </div>
        ) : interviewApps.length === 0 ? (
          <div style={{
            padding: 'var(--space-12)',
            textAlign: 'center',
            border: '1px solid var(--border)',
            borderRadius: 12,
            color: 'var(--text-secondary)'
          }}>
            No interviews scheduled for this workspace. Use the Dashboard or Pipeline Board to schedule candidates.
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
            {interviewApps.map((app) => (
              <div 
                key={app.id}
                style={{
                  border: '1px solid var(--color-cork-shadow)',
                  borderRadius: 12,
                  padding: 'var(--space-4)',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center'
                }}
              >
                <div>
                  <h3 style={{ fontSize: '18px', fontWeight: 500, color: 'var(--text)', margin: 0 }}>
                    {app.candidate?.full_name || 'Candidate Interview'}
                  </h3>
                  <div style={{ display: 'flex', gap: 12, marginTop: 4, fontSize: 12, color: 'var(--text-secondary)' }}>
                    <span>Role: {app.job?.title || 'Unknown Role'}</span>
                    <span>&bull;</span>
                    <span>Stage: {app.status.toUpperCase()}</span>
                  </div>
                </div>
                <div>
                  <span className="badge badge--interview" style={{ fontSize: 10 }}>Scheduled</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </AppLayout>
  )
}
