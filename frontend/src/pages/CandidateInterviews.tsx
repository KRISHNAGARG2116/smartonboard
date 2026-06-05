import CandidateLayout from '../components/CandidateLayout'

export default function CandidateInterviews() {
  return (
    <CandidateLayout>
      <div className="container" style={{ padding: 'var(--space-6) 0' }}>
        <div className="card card__body">
          <h3 style={{ fontSize: 'var(--text-lg)', fontWeight: 700, marginBottom: 'var(--space-2)' }}>My Interviews</h3>
          <p style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-sm)', marginBottom: 'var(--space-6)' }}>
            View and manage your scheduled interview slots.
          </p>
          <div className="empty-state">
            <span style={{ fontSize: '48px', marginBottom: 'var(--space-3)' }}>📅</span>
            <h4 className="empty-state__title">No Interviews Scheduled</h4>
            <p className="empty-state__desc" style={{ marginBottom: 'var(--space-4)' }}>
              Interview calendar synchronization and scheduling slots booking are coming in Phase F.
            </p>
          </div>
        </div>
      </div>
    </CandidateLayout>
  )
}
