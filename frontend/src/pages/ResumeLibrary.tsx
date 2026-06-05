import CandidateLayout from '../components/CandidateLayout'

export default function ResumeLibrary() {
  return (
    <CandidateLayout>
      <div className="container" style={{ padding: 'var(--space-6) 0' }}>
        <div className="card card__body">
          <h3 style={{ fontSize: 'var(--text-lg)', fontWeight: 700, marginBottom: 'var(--space-2)' }}>Resume Library</h3>
          <p style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-sm)', marginBottom: 'var(--space-6)' }}>
            Upload and manage your professional resumes. You can upload up to 3 resumes for matching.
          </p>
          <div className="empty-state">
            <span style={{ fontSize: '48px', marginBottom: 'var(--space-3)' }}>📄</span>
            <h4 className="empty-state__title">No Resumes Uploaded Yet</h4>
            <p className="empty-state__desc" style={{ marginBottom: 'var(--space-4)' }}>
              Resume upload and library management features are coming in Phase D.
            </p>
          </div>
        </div>
      </div>
    </CandidateLayout>
  )
}
