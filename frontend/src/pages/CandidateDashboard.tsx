import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import CandidateLayout from '../components/CandidateLayout'
import { fetchCandidateResumes } from '../api'

export default function CandidateDashboard() {
  const { user } = useAuth()
  const [resumesCount, setResumesCount] = useState(0)

  useEffect(() => {
    fetchCandidateResumes()
      .then(resumes => setResumesCount(resumes.length))
      .catch(() => {})
  }, [])

  // Placeholder data for foundation phase
  const stats = {
    resumesUploaded: resumesCount,
    maxResumes: 3,
    activeApplications: 2,
    scheduledInterviews: 1,
    emailVerified: true,
    phoneVerified: false,
    profileCompletion: resumesCount > 0 ? 80 : 50,
  }

  const pendingTasks = [
    { name: 'Verify your phone number via SMS OTP', route: '/candidate/profile', type: 'verification' },
    ...(resumesCount === 0 
      ? [{ name: 'Upload your primary resume to start matching', route: '/candidate/resumes', type: 'resume' }]
      : resumesCount < 3 
        ? [{ name: 'Upload a secondary backup resume', route: '/candidate/resumes', type: 'resume' }]
        : []
    ),
    { name: 'Complete your profile information details', route: '/candidate/profile', type: 'profile' }
  ]

  return (
    <CandidateLayout>
      <div className="container" style={{ padding: 'var(--space-6) 0 var(--space-12)' }}>
        {/* Welcome Section */}
        <div 
          className="card" 
          style={{ 
            background: 'linear-gradient(135deg, var(--bg-subtle) 0%, var(--surface) 100%)', 
            padding: 'var(--space-6)', 
            border: '1px solid var(--border)',
            borderRadius: '16px',
            marginBottom: 'var(--space-6)',
            boxShadow: 'var(--shadow-sm)'
          }}
        >
          <h1 style={{ fontSize: 'var(--text-2xl)', fontWeight: 800, letterSpacing: '-0.02em', color: 'var(--text)' }}>
            Welcome back, {user?.full_name || 'Candidate'}!
          </h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-sm)', marginTop: 'var(--space-1)' }}>
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
              {/* Resumes Count Card */}
              <Link to="/candidate/resumes" className="card card__body" style={{ textDecoration: 'none', transition: 'transform 150ms ease' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)', fontWeight: 600 }}>Resumes</span>
                  <span style={{ fontSize: '18px' }}>📄</span>
                </div>
                <div style={{ fontSize: 'var(--text-3xl)', fontWeight: 800, marginTop: 'var(--space-3)' }}>
                  {stats.resumesUploaded} <span style={{ fontSize: 'var(--text-sm)', color: 'var(--text-tertiary)', fontWeight: 500 }}>/ {stats.maxResumes}</span>
                </div>
                <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: 'var(--space-2)' }}>
                  Active & verified in library
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
                  Upcoming live calendar events
                </div>
              </Link>
            </div>

            {/* Verification Status & Action Checklist */}
            <div className="card">
              <div className="card__header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <h3 style={{ fontSize: 'var(--text-base)', fontWeight: 700 }}>Verification Checklist</h3>
                <span className="badge badge--neutral" style={{ fontSize: '10px' }}>Action Required</span>
              </div>
              <div className="card__body" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
                {pendingTasks.map((task, idx) => (
                  <div 
                    key={idx} 
                    style={{ 
                      display: 'flex', 
                      alignItems: 'center', 
                      gap: 'var(--space-3)', 
                      padding: 'var(--space-3)', 
                      background: 'var(--bg-subtle)', 
                      borderRadius: '10px',
                      border: '1px solid var(--border)'
                    }}
                  >
                    <span style={{ fontSize: '16px' }}>⚠️</span>
                    <span style={{ flex: 1, fontSize: 'var(--text-sm)', fontWeight: 550 }}>{task.name}</span>
                    <Link to={task.route} className="btn btn--primary btn--sm" style={{ borderRadius: '8px' }}>
                      Resolve
                    </Link>
                  </div>
                ))}
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
                    background: `conic-gradient(var(--accent) ${stats.profileCompletion}%, var(--border) 0)`,
                    display: 'grid',
                    placeItems: 'center'
                  }}
                >
                  <div 
                    style={{ 
                      position: 'absolute', 
                      inset: '6px', 
                      borderRadius: '50%', 
                      background: 'var(--surface)', 
                      display: 'grid', 
                      placeItems: 'center',
                      fontSize: 'var(--text-sm)',
                      fontWeight: 750
                    }}
                  >
                    {stats.profileCompletion}%
                  </div>
                </div>
                <div>
                  <h4 style={{ fontSize: 'var(--text-sm)', fontWeight: 750 }}>Almost there!</h4>
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
                  <span className="badge badge--hire">Verified</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 'var(--text-sm)' }}>
                  <span>Phone Verification</span>
                  <span className="badge badge--interview">Pending OTP</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 'var(--text-sm)' }}>
                  <span>Identity Proof</span>
                  <span className="badge badge--reject" style={{ background: 'var(--bg-subtle)', color: 'var(--text-tertiary)' }}>Unlinked</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </CandidateLayout>
  )
}
