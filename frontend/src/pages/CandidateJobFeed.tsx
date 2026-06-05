import CandidateLayout from '../components/CandidateLayout'

export default function CandidateJobFeed() {
  return (
    <CandidateLayout>
      <div className="container" style={{ padding: 'var(--space-6) 0' }}>
        <div className="card card__body">
          <h3 style={{ fontSize: 'var(--text-lg)', fontWeight: 700, marginBottom: 'var(--space-2)' }}>Explore Jobs</h3>
          <p style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-sm)', marginBottom: 'var(--space-6)' }}>
            Discover job openings you are genuinely qualified for.
          </p>
          <div className="empty-state">
            <span style={{ fontSize: '48px', marginBottom: 'var(--space-3)' }}>🔍</span>
            <h4 className="empty-state__title">Job Feed Offline</h4>
            <p className="empty-state__desc" style={{ marginBottom: 'var(--space-4)' }}>
              Personalized job feed and applicability matching features are coming in Phase E.
            </p>
          </div>
        </div>
      </div>
    </CandidateLayout>
  )
}
