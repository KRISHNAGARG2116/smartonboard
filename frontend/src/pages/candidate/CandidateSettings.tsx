import CandidateLayout from '../../components/CandidateLayout'

export default function CandidateSettings() {
  return (
    <CandidateLayout>
      <div className="container" style={{ padding: 'var(--space-6) 0 var(--space-12)' }}>
        {/* Header */}
        <div style={{
          borderBottom: '1px dashed var(--color-cork-shadow)',
          paddingBottom: 'var(--space-6)',
          marginBottom: 'var(--space-6)'
        }}>
          <span style={{ fontSize: 10, fontWeight: 500, color: 'var(--text-secondary)', letterSpacing: '0.05em', textTransform: 'uppercase' }}>
            Candidate Hub
          </span>
          <h1 style={{ fontSize: '29px', fontWeight: 500, letterSpacing: '-0.02em', color: 'var(--text)', margin: '4px 0 0', lineHeight: 1.09 }}>
            Profile Preferences
          </h1>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '3fr 2fr', gap: 'var(--space-6)', alignItems: 'flex-start' }}>
          {/* Main settings card */}
          <div className="card card__body">
            <h2 style={{ fontSize: '18px', fontWeight: 500, margin: '0 0 16px', color: 'var(--text)' }}>
              Account Configurations
            </h2>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              <div>
                <label style={{ display: 'block', fontSize: 10, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 4 }}>
                  Profile Visibility Status
                </label>
                <div style={{ fontSize: 14, color: 'var(--text)', marginTop: 4 }}>
                  Verified Recruiter Matches Only (Active)
                </div>
              </div>
              <div>
                <label style={{ display: 'block', fontSize: 10, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 4 }}>
                  Match Percentages Visibility
                </label>
                <div style={{ fontSize: 14, color: 'var(--text)', marginTop: 4 }}>
                  Show matching metrics on job cards (Active)
                </div>
              </div>
            </div>
          </div>

          {/* Right sidebar info */}
          <div className="card card__body" style={{ borderStyle: 'dashed', color: 'var(--text-secondary)' }}>
            <h3 style={{ fontSize: '14px', fontWeight: 500, color: 'var(--text)', margin: '0 0 8px' }}>
              Verification Rules
            </h3>
            <p style={{ fontSize: 13, lineHeight: 1.35, margin: 0 }}>
              To update your SMS/Phone verification or change your verified email parameters, please visit the main Verification Center under your profile settings.
            </p>
          </div>
        </div>
      </div>
    </CandidateLayout>
  )
}
