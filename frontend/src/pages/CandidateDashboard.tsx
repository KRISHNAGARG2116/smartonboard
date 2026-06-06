import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import CandidateLayout from '../components/CandidateLayout'
import CandidateOnboardingWizard from '../components/CandidateOnboardingWizard'
import { 
  fetchCandidateResumes, 
  fetchCandidateProfile, 
  fetchMyApplications, 
  fetchMyInterviews 
} from '../api'

export default function CandidateDashboard() {
  const { user } = useAuth()
  const [hasOnboarded, setHasOnboarded] = useState(() => {
    return localStorage.getItem(`oryzo_onboarded_candidate_${user?.email}`) === 'true'
  })
  const [resumesCount, setResumesCount] = useState(0)
  const [applicationsCount, setApplicationsCount] = useState(0)
  const [interviewsCount, setInterviewsCount] = useState(0)
  const [profile, setProfile] = useState<{ email_verified: boolean; phone_verified: boolean } | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      fetchCandidateResumes().then(resumes => setResumesCount(resumes.length)).catch(() => {}),
      fetchMyApplications().then(apps => setApplicationsCount(apps.length)).catch(() => {}),
      fetchMyInterviews().then(ivs => setInterviewsCount(ivs.filter(i => !i.is_cancelled).length)).catch(() => {}),
      fetchCandidateProfile().then(data => {
        if (data && data.profile) {
          setProfile(data.profile)
        }
      }).catch(() => {})
    ]).finally(() => {
      setLoading(false)
    })
  }, [])

  if (!hasOnboarded) {
    return (
      <CandidateOnboardingWizard
        onComplete={() => {
          localStorage.setItem(`oryzo_onboarded_candidate_${user?.email}`, 'true')
          setHasOnboarded(true)
        }}
      />
    )
  }

  const stats = {
    resumesUploaded: resumesCount,
    maxResumes: 3,
    activeApplications: applicationsCount,
    scheduledInterviews: interviewsCount,
    emailVerified: profile?.email_verified ?? false,
    phoneVerified: profile?.phone_verified ?? false,
    profileCompletion: (resumesCount > 0 ? 40 : 0) + 
                       ((profile?.email_verified ?? false) ? 30 : 0) + 
                       ((profile?.phone_verified ?? false) ? 30 : 0),
  }

  const pendingTasks = [
    ...(!stats.emailVerified 
      ? [{ name: 'Verify your email address via OTP', route: '/candidate/profile', type: 'verification' }]
      : []
    ),
    ...(!stats.phoneVerified 
      ? [{ name: 'Verify your phone number via SMS OTP', route: '/candidate/profile', type: 'verification' }]
      : []
    ),
    ...(resumesCount === 0 
      ? [{ name: 'Upload your primary resume to start matching', route: '/candidate/resumes', type: 'resume' }]
      : resumesCount < 3 
        ? [{ name: 'Upload a secondary backup resume', route: '/candidate/resumes', type: 'resume' }]
        : []
    )
  ]

  return (
    <CandidateLayout>
      <div className="container" style={{ padding: 'var(--space-6) 0 var(--space-12)' }}>
        {/* Welcome Section */}
        <div 
          className="card" 
          style={{ 
            background: 'transparent', 
            padding: 'var(--space-6)', 
            border: '1px dashed var(--color-cork-shadow)',
            borderRadius: '12px',
            marginBottom: 'var(--space-6)',
            boxShadow: 'none'
          }}
        >
          <h1 style={{ fontSize: '29px', fontWeight: 500, letterSpacing: '-0.02em', color: 'var(--text)', lineHeight: 1.09 }}>
            Welcome back, {user?.full_name || 'Candidate'}!
          </h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '14px', marginTop: 'var(--space-1)', lineHeight: 1.33 }}>
            Track your job applications, manage resumes, and prepare for upcoming interviews.
          </p>
        </div>

        <div className="dashboard-grid">
          {/* Main Content Column */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)' }}>
            {/* Overview Stats Cards */}
            <div 
              style={{ 
                display: 'grid', 
                gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', 
                gap: 'var(--space-4)' 
              }}
            >
              {/* Resume Library Card */}
              <Link to="/candidate/resumes" className="card card__body" style={{ textDecoration: 'none', transition: 'transform 150ms ease' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)', fontWeight: 600 }}>Resume Status</span>
                  <span style={{ fontSize: '18px' }}>📄</span>
                </div>
                <div style={{ fontSize: 'var(--text-3xl)', fontWeight: 800, marginTop: 'var(--space-3)' }}>
                  {stats.resumesUploaded} <span style={{ fontSize: 'var(--text-sm)', color: 'var(--text-tertiary)', fontWeight: 500 }}>/ {stats.maxResumes}</span>
                </div>
                <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: 'var(--space-2)' }}>
                  Active resume documents
                </div>
              </Link>

              {/* Applications Card */}
              <Link to="/candidate/applications" className="card card__body" style={{ textDecoration: 'none', transition: 'transform 150ms ease' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)', fontWeight: 600 }}>Applications</span>
                  <span style={{ fontSize: '18px' }}>📨</span>
                </div>
                <div style={{ fontSize: 'var(--text-3xl)', fontWeight: 800, marginTop: 'var(--space-3)' }}>
                  {stats.activeApplications}
                </div>
                <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: 'var(--space-2)' }}>
                  Submitted job applications
                </div>
              </Link>

              {/* Interviews Card */}
              <Link to="/candidate/interviews" className="card card__body" style={{ textDecoration: 'none', transition: 'transform 150ms ease' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)', fontWeight: 600 }}>Interviews</span>
                  <span style={{ fontSize: '18px' }}>📅</span>
                </div>
                <div style={{ fontSize: 'var(--text-3xl)', fontWeight: 800, marginTop: 'var(--space-3)' }}>
                  {stats.scheduledInterviews}
                </div>
                <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: 'var(--space-2)' }}>
                  Upcoming calendar events
                </div>
              </Link>
            </div>

            {/* Career Progress Tracker */}
            <div className="card card__body">
              <h3 style={{ fontSize: 'var(--text-sm)', fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: 12 }}>
                Career Progress Pipeline
              </h3>
              <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                fontSize: 12,
                color: 'var(--text-secondary)',
                borderTop: '1px dashed var(--color-cork-shadow)',
                paddingTop: 12
              }}>
                <span style={{ color: 'var(--text)', fontWeight: 600 }}>1. Register &bull; OK</span>
                <span style={{ color: stats.resumesUploaded > 0 ? 'var(--text)' : 'var(--color-burnt-sienna)', fontWeight: 600 }}>
                  2. Upload Resume {stats.resumesUploaded > 0 ? '&bull; OK' : ''}
                </span>
                <span style={{ color: stats.phoneVerified ? 'var(--text)' : 'var(--color-burnt-sienna)', fontWeight: 600 }}>
                  3. Verify Profile {stats.phoneVerified ? '&bull; OK' : ''}
                </span>
                <span>4. Sourcing &bull; Active</span>
              </div>
            </div>

            {/* Verification Status & Action Checklist */}
            <div className="card">
              <div className="card__header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <h3 style={{ fontSize: 'var(--text-base)', fontWeight: 700 }}>Verification Checklist</h3>
                {pendingTasks.length > 0 ? (
                  <span className="badge badge--neutral" style={{ fontSize: '10px' }}>Action Required</span>
                ) : (
                  <span className="badge badge--hire" style={{ fontSize: '10px' }}>Completed</span>
                )}
              </div>
              <div className="card__body" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
                {loading ? (
                  <div style={{ padding: 'var(--space-4)', textAlign: 'center', color: 'var(--text-secondary)' }}>
                    Loading checklist...
                  </div>
                ) : pendingTasks.length === 0 ? (
                  <div style={{ textAlign: 'center', padding: 'var(--space-4)', color: 'var(--text-secondary)', fontSize: 'var(--text-sm)' }}>
                    ✅ All verification and profile setup steps are complete!
                  </div>
                ) : (
                  pendingTasks.map((task, idx) => (
                    <div 
                      key={idx} 
                      style={{ 
                        display: 'flex', 
                        alignItems: 'center', 
                        gap: 'var(--space-3)', 
                        padding: 'var(--space-3)', 
                        background: 'transparent', 
                        borderRadius: '12px',
                        border: '1px dashed var(--color-cork-shadow)'
                      }}
                    >
                      <span style={{ fontSize: '16px' }}>⚠️</span>
                      <span style={{ flex: 1, fontSize: '14px', fontWeight: 500, color: 'var(--text)' }}>{task.name}</span>
                      <Link to={task.route} className="btn btn--primary btn--sm" style={{ borderRadius: '36px' }}>
                        Resolve
                      </Link>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Recommended Jobs Card */}
            <div className="card">
              <div className="card__header">
                <h3 style={{ fontSize: 'var(--text-base)', fontWeight: 700 }}>Recommended Matching Jobs</h3>
              </div>
              <div className="card__body" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
                <div style={{
                  border: '1px solid var(--color-cork-shadow)',
                  borderRadius: 12,
                  padding: 16,
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center'
                }}>
                  <div>
                    <h4 style={{ fontSize: 16, fontWeight: 500, margin: 0 }}>Lead Frontend Engineer</h4>
                    <span style={{ fontSize: 11, color: 'var(--text-secondary)' }}>Required: React, TypeScript, TailwindCSS</span>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontSize: 16, fontWeight: 800, color: 'var(--text)' }}>94% Match</div>
                    <Link to="/candidate/jobs" style={{ fontSize: 12, color: 'var(--color-burnt-sienna)', textDecoration: 'underline' }}>View details</Link>
                  </div>
                </div>

                <div style={{
                  border: '1px solid var(--color-cork-shadow)',
                  borderRadius: 12,
                  padding: 16,
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center'
                }}>
                  <div>
                    <h4 style={{ fontSize: 16, fontWeight: 500, margin: 0 }}>Senior Fullstack Developer</h4>
                    <span style={{ fontSize: 11, color: 'var(--text-secondary)' }}>Required: Node.js, Python, PostgreSQL</span>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontSize: 16, fontWeight: 800, color: 'var(--text)' }}>88% Match</div>
                    <Link to="/candidate/jobs" style={{ fontSize: 12, color: 'var(--color-burnt-sienna)', textDecoration: 'underline' }}>View details</Link>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Right Sidebar Column */}
          <div className="dashboard-sidebar" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)' }}>
            {/* Profile Completion Card */}
            <div className="card card__body">
              <h3 style={{ fontSize: 'var(--text-sm)', fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                Profile Completion
              </h3>
              <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-4)', marginTop: 'var(--space-4)' }}>
                <div 
                  style={{ 
                    position: 'relative', 
                    width: '64px', 
                    height: '64px', 
                    borderRadius: '50%', 
                    background: `conic-gradient(var(--color-warm-cream) ${stats.profileCompletion}%, var(--color-cork-shadow) 0)`,
                    display: 'grid',
                    placeItems: 'center'
                  }}
                >
                  <div 
                    style={{ 
                      position: 'absolute', 
                      inset: '6px', 
                      borderRadius: '50%', 
                      background: 'var(--bg)', 
                      display: 'grid', 
                      placeItems: 'center',
                      fontSize: '14px',
                      fontWeight: 500,
                      color: 'var(--text)'
                    }}
                  >
                    {stats.profileCompletion}%
                  </div>
                </div>
                <div>
                  <h4 style={{ fontSize: '14px', fontWeight: 500, color: 'var(--text)' }}>Almost there!</h4>
                  <p style={{ fontSize: 'var(--text-xs)', color: 'var(--text-secondary)', marginTop: '2px', lineHeight: 1.3 }}>
                    Verify your phone number and load your credentials to unlock applicability matching.
                  </p>
                </div>
              </div>
            </div>

            {/* Trust & Verification Status Card */}
            <div className="card">
              <div className="card__header">
                <h3 style={{ fontSize: 'var(--text-sm)', fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                  Trust Signals
                </h3>
              </div>
              <div className="card__body" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 'var(--text-sm)' }}>
                  <span>Email Verification</span>
                  {stats.emailVerified ? (
                    <span className="badge badge--hire">Verified</span>
                  ) : (
                    <span className="badge badge--reject">Unverified</span>
                  )}
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 'var(--text-sm)' }}>
                  <span>Phone Verification</span>
                  {stats.phoneVerified ? (
                    <span className="badge badge--hire">Verified</span>
                  ) : (
                    <span className="badge badge--interview">Pending OTP</span>
                  )}
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 'var(--text-sm)' }}>
                  <span>Identity Proof</span>
                  <span className="badge badge--neutral">Unlinked</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </CandidateLayout>
  )
}
