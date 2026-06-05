import CandidateLayout from '../components/CandidateLayout'

export default function CandidateApplications() {
  return (
    <CandidateLayout>
      <div className="container" style={{ padding: 'var(--space-6) 0' }}>
        <div className="card card__body">
          <h3 style={{ fontSize: 'var(--text-lg)', fontWeight: 700, marginBottom: 'var(--space-2)' }}>My Applications</h3>
          <p style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-sm)', marginBottom: 'var(--space-6)' }}>
            Track the status of your submitted job applications.
          </p>
          <div className="empty-state">
            <span style={{ fontSize: '48px', marginBottom: 'var(--space-3)' }}>📨</span>
            <h4 className="empty-state__title">No Applications Yet</h4>
            <p className="empty-state__desc" style={{ marginBottom: 'var(--space-4)' }}>
              Job applications list and interview tracking logs are coming in Phase F.
            </p>
          </div>
        </div>
      </div>
    </CandidateLayout>
  )
}
