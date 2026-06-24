import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import CandidateLayout from '../components/CandidateLayout'
import {
  fetchMyApplications,
  withdrawApplication,
  type CandidateApplicationItem
} from '../api'

export default function CandidateApplications() {
  const [applications, setApplications] = useState<CandidateApplicationItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Drawer / Selection state
  const [selectedApp, setSelectedApp] = useState<CandidateApplicationItem | null>(null)
  
  // Submit state
  const [withdrawingId, setWithdrawingId] = useState<string | null>(null)
  const [withdrawSuccess, setWithdrawSuccess] = useState<string | null>(null)

  const loadApplications = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchMyApplications()
      setApplications(data)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to retrieve applications. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadApplications()
  }, [])

  const handleWithdraw = async (appId: string) => {
    if (!window.confirm("Are you sure you want to withdraw this application? This action is permanent and cannot be undone.")) {
      return
    }
    setWithdrawingId(appId)
    setWithdrawSuccess(null)
    try {
      await withdrawApplication(appId)
      setWithdrawSuccess("Your application has been successfully withdrawn.")
      // Reload lists
      const freshApps = await fetchMyApplications()
      setApplications(freshApps)
      // Update selected drawer application if open
      const updated = freshApps.find(a => a.id === appId)
      if (updated) setSelectedApp(updated)
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to withdraw application. Please try again.')
    } finally {
      setWithdrawingId(null)
    }
  }

  const getStatusBadgeStyle = (status: string) => {
    const s = status.toLowerCase()
    if (s === 'submitted') {
      return { border: '1px solid var(--border)', background: 'transparent', color: 'var(--text)', label: 'Applied' }
    } else if (s === 'screening') {
      return { border: '1px solid var(--color-grey-brown)', background: 'transparent', color: 'var(--color-grey-brown)', label: 'Reviewing' }
    } else if (s === 'interview') {
      return { border: '1px solid var(--color-burnt-sienna)', background: 'transparent', color: 'var(--color-burnt-sienna)', label: 'Interview' }
    } else if (s === 'offer') {
      return { border: '1px solid var(--color-burnt-sienna)', background: 'transparent', color: 'var(--color-burnt-sienna)', label: 'Offer Extended' }
    } else if (s === 'hired') {
      return { border: '1px solid var(--border)', background: 'transparent', color: 'var(--text)', label: 'Hired' }
    } else if (s === 'rejected') {
      return { border: '1px solid var(--color-cork-shadow)', background: 'transparent', color: 'var(--color-grey-brown)', label: 'Declined' }
    } else {
      return { border: '1px solid var(--color-cork-shadow)', background: 'transparent', color: 'var(--color-grey-brown)', label: 'Withdrawn' }
    }
  }

  return (
    <CandidateLayout>
      <div className="container" style={{ padding: 'var(--space-6) 0 var(--space-12)' }}>
        <div style={{ maxWidth: '960px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: 'var(--space-6)' }}>
          
          {/* Header Card */}
          <div className="card card__body">
            <h3 style={{ fontSize: '29px', fontWeight: 500, letterSpacing: '-0.02em', marginBottom: 'var(--space-2)', lineHeight: 1.09, color: 'var(--text)' }}>My Applications</h3>
            <p style={{ color: 'var(--color-grey-brown)', fontSize: '14px', lineHeight: 1.33, marginBottom: 0 }}>
              Track the progress and history of your submitted job applications. View historical resume and profile snapshots.
            </p>
          </div>

          {error && (
            <div className="card card__body" style={{ border: '1px solid var(--danger)', background: 'var(--danger-bg)', color: 'var(--text)', borderRadius: '16px' }}>
              <strong>Error:</strong> {error}
            </div>
          )}

          {withdrawSuccess && (
            <div className="card card__body" style={{ border: '1px solid var(--border)', background: 'var(--color-pure-white)', color: 'var(--text)', borderRadius: '16px' }}>
              {withdrawSuccess}
            </div>
          )}

          {/* Applications list */}
          {loading ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
              {[1, 2].map(i => (
                <div key={i} className="card card__body" style={{ height: '100px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', opacity: 0.6, animation: 'pulse 1.5s infinite' }}>
                  <div style={{ width: '30%', height: '16px', background: 'var(--border)', borderRadius: '4px' }}></div>
                  <div style={{ width: '50%', height: '12px', background: 'var(--border)', borderRadius: '4px' }}></div>
                </div>
              ))}
            </div>
          ) : applications.length === 0 ? (
            <div className="card card__body" style={{ textAlign: 'center', padding: 'var(--space-12) var(--space-6)' }}>
              <span style={{ fontSize: '48px', display: 'block', marginBottom: 'var(--space-4)' }}>📨</span>
              <h4 style={{ fontSize: '18px', fontWeight: 500, color: 'var(--text)', marginBottom: 'var(--space-2)' }}>No Applications Yet</h4>
              <p style={{ color: 'var(--color-grey-brown)', fontSize: '14px', margin: 0 }}>
                You have not submitted any job applications yet. Go to the <Link to="/candidate/jobs" style={{ color: 'var(--color-burnt-sienna)', textDecoration: 'underline' }}>Jobs Feed</Link> to apply.
              </p>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
              {applications.map((app) => {
                const styleBadge = getStatusBadgeStyle(app.status)
                return (
                  <div 
                    key={app.id} 
                    className="card card__body"
                    style={{ 
                      display: 'flex', 
                      justifyContent: 'space-between', 
                      alignItems: 'center', 
                      cursor: 'pointer',
                      transition: 'transform 150ms ease, border-color 150ms ease'
                    }}
                    onClick={() => {
                      setWithdrawSuccess(null)
                      setSelectedApp(app)
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.borderColor = 'var(--color-warm-cream)'
                      e.currentTarget.style.transform = 'translateY(-1px)'
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.borderColor = 'var(--color-cork-shadow)'
                      e.currentTarget.style.transform = 'translateY(0)'
                    }}
                  >
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-1)', minWidth: 0, flex: 1 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)', flexWrap: 'wrap' }}>
                        <h4 style={{ fontSize: '15px', fontWeight: 500, margin: 0, color: 'var(--text)' }}>{app.job_title}</h4>
                        <span 
                          style={{ 
                            fontSize: '10px', 
                            fontWeight: 500, 
                            padding: '3px 8px', 
                            borderRadius: '999px',
                            border: styleBadge.border,
                            background: styleBadge.background,
                            color: styleBadge.color
                          }}
                        >
                          {styleBadge.label}
                        </span>
                      </div>
                      <p style={{ color: 'var(--color-grey-brown)', fontSize: '12px', margin: 0 }}>
                        {app.company_name} · <strong>{app.job_department}</strong>
                      </p>
                      <span style={{ fontSize: '10px', color: 'var(--color-grey-brown)' }}>
                        Applied on {new Date(app.created_at).toLocaleDateString()}
                      </span>
                    </div>

                    <div style={{ flexShrink: 0 }}>
                      <button 
                        type="button" 
                        className="btn btn--secondary btn--sm" 
                        style={{ padding: '8px 14px' }}
                        onClick={(e) => {
                          e.stopPropagation()
                          setWithdrawSuccess(null)
                          setSelectedApp(app)
                        }}
                      >
                        Review Snapshot →
                      </button>
                    </div>
                  </div>
                )
              })}
            </div>
          )}

        </div>
      </div>

      {/* Slide-out Application Snapshot Drawer */}
      {selectedApp && (
        <>
          <div 
            onClick={() => setSelectedApp(null)}
            style={{
              position: 'fixed',
              inset: 0,
              background: 'rgba(16,9,4,0.7)',
              zIndex: 999
            }}
          />
          <aside
            role="dialog"
            aria-modal="true"
            aria-labelledby="drawer-app-title"
            style={{
              position: 'fixed',
              top: 0,
              right: 0,
              bottom: 0,
              width: 'min(560px, 100vw)',
              background: 'var(--surface)',
              borderLeft: '1px solid var(--color-cork-shadow)',
              display: 'flex',
              flexDirection: 'column',
              zIndex: 1000,
              
              overflow: 'hidden'
            }}
          >
            {/* Drawer Header */}
            <div 
              style={{ 
                padding: 'var(--space-6)', 
                borderBottom: '1px solid var(--color-cork-shadow)', 
                display: 'flex', 
                justifyContent: 'space-between', 
                alignItems: 'flex-start' 
              }}
            >
              <div>
                <h2 id="drawer-app-title" style={{ fontSize: '18px', fontWeight: 500, color: 'var(--text)', margin: 0 }}>
                  {selectedApp.job_title}
                </h2>
                <p style={{ fontSize: '12px', color: 'var(--color-grey-brown)', marginTop: '4px', margin: 0 }}>
                  {selectedApp.company_name} · {selectedApp.job_department}
                </p>
              </div>
              <button
                type="button"
                className="icon-btn"
                onClick={() => setSelectedApp(null)}
                style={{ 
                  border: '1px solid var(--color-cork-shadow)', 
                  borderRadius: '50%', 
                  width: '32px', 
                  height: '32px', 
                  display: 'grid', 
                  placeItems: 'center',
                  background: 'transparent',
                  color: 'var(--text)'
                }}
                aria-label="Close Snapshot Drawer"
              >
                ✕
              </button>
            </div>

            {/* Drawer Body Scroll Content */}
            <div style={{ flex: 1, overflowY: 'auto', padding: 'var(--space-6)', display: 'flex', flexDirection: 'column', gap: 'var(--space-6)' }}>
              
              {/* Application Status Timeline indicator */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
                <h4 style={{ fontSize: '10px', fontWeight: 500, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--color-grey-brown)', margin: 0 }}>
                  Progress Pipeline
                </h4>
                <div 
                  style={{ 
                    padding: 'var(--space-4)', 
                    background: 'transparent', 
                    borderRadius: 'var(--radius-cards)', 
                    border: '1px solid var(--border)',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '12px'
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: '14px', fontWeight: 500, color: 'var(--text)' }}>Hiring Stage Status</span>
                    <span 
                      style={{ 
                        fontSize: '10px', 
                        fontWeight: 500, 
                        padding: '3px 8px', 
                        borderRadius: '999px',
                        ...getStatusBadgeStyle(selectedApp.status)
                      }}
                    >
                      {getStatusBadgeStyle(selectedApp.status).label}
                    </span>
                  </div>
                  <span style={{ fontSize: '10px', color: 'var(--color-grey-brown)', lineHeight: 1.3 }}>
                    * Historical snapshots are immutable records of your profile fields at application time. Future profile edits will not alter this snapshot.
                  </span>
                </div>
              </div>

              {/* Frozen Snapshot Details */}
              {selectedApp.snapshot ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)' }}>
                  
                  {/* Candidate Profile fields Snapshot */}
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
                    <h4 style={{ fontSize: '10px', fontWeight: 500, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--color-grey-brown)', margin: 0 }}>
                      Profile Snapshot
                    </h4>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)', border: '1px solid var(--border)', padding: 'var(--space-4)', borderRadius: 'var(--radius-cards)' }}>
                      <div style={{ display: 'grid', gridTemplateColumns: '120px 1fr', gap: '8px', fontSize: '14px' }}>
                        <span style={{ color: 'var(--color-grey-brown)', fontWeight: 400 }}>Full Name:</span>
                        <strong style={{ color: 'var(--text)', fontWeight: 500 }}>{selectedApp.snapshot.candidate_snapshot.full_name}</strong>

                        <span style={{ color: 'var(--color-grey-brown)', fontWeight: 400 }}>Email Address:</span>
                        <span style={{ color: 'var(--text)', wordBreak: 'break-all' }}>{selectedApp.snapshot.candidate_snapshot.email}</span>

                        <span style={{ color: 'var(--color-grey-brown)', fontWeight: 400 }}>Phone Number:</span>
                        <span style={{ color: 'var(--text)' }}>{selectedApp.snapshot.candidate_snapshot.phone_number || 'N/A'}</span>

                        <span style={{ color: 'var(--color-grey-brown)', fontWeight: 400 }}>Location:</span>
                        <span style={{ color: 'var(--text)' }}>{selectedApp.snapshot.candidate_snapshot.location || 'N/A'}</span>
                      </div>
                    </div>
                  </div>

                  {/* Resume details Snapshot */}
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
                    <h4 style={{ fontSize: '10px', fontWeight: 500, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--color-grey-brown)', margin: 0 }}>
                      Resume Library snapshot
                    </h4>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)', border: '1px solid var(--border)', padding: 'var(--space-4)', borderRadius: 'var(--radius-cards)' }}>
                      <div>
                        <span style={{ fontSize: '10px', color: 'var(--color-grey-brown)', display: 'block' }}>Submitted Resume File:</span>
                        <strong style={{ fontSize: '14px', fontWeight: 500, color: 'var(--text)' }}>📄 {selectedApp.snapshot.resume_snapshot.filename}</strong>
                      </div>
                      
                      {selectedApp.snapshot.resume_snapshot.parsed_summary && (
                        <div>
                          <span style={{ fontSize: '10px', color: 'var(--color-grey-brown)', display: 'block', marginBottom: '4px' }}>Extracted Summary:</span>
                          <p style={{ fontSize: '12px', color: 'var(--color-grey-brown)', margin: 0, lineHeight: 1.5, fontStyle: 'italic' }}>
                            "{selectedApp.snapshot.resume_snapshot.parsed_summary}"
                          </p>
                        </div>
                      )}
                      
                      {selectedApp.snapshot.resume_snapshot.parsed_skills.length > 0 && (
                        <div>
                          <span style={{ fontSize: '10px', color: 'var(--color-grey-brown)', display: 'block', marginBottom: '6px' }}>Extracted Skills:</span>
                          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                            {selectedApp.snapshot.resume_snapshot.parsed_skills.map((skill, idx) => (
                              <span 
                                key={idx} 
                                style={{ 
                                  fontSize: '10px', 
                                  padding: '3px 8px', 
                                  borderRadius: '9999px', 
                                  background: 'transparent', 
                                  color: 'var(--color-grey-brown)',
                                  border: '1px solid var(--color-cork-shadow)'
                                }}
                              >
                                {skill}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>

                </div>
              ) : (
                <div style={{ textAlign: 'center', color: 'var(--color-grey-brown)', fontSize: '12px', padding: 'var(--space-6) 0' }}>
                  No historical snapshot metadata found for this application.
                </div>
              )}

            </div>

            {/* Drawer Footer Withdrawal Action Panel */}
            {selectedApp.status.toLowerCase() !== 'withdrawn' && selectedApp.status.toLowerCase() !== 'rejected' && (
              <div 
                style={{ 
                  padding: 'var(--space-6)', 
                  borderTop: '1px solid var(--color-cork-shadow)', 
                  background: 'transparent'
                }}
              >
                <button
                  type="button"
                  className="btn btn--secondary"
                  disabled={withdrawingId === selectedApp.id}
                  onClick={() => handleWithdraw(selectedApp.id)}
                  style={{ 
                    width: '100%', 
                    padding: '12px', 
                    borderRadius: 'var(--radius-buttons)', 
                    fontWeight: 500,
                    border: '1px solid var(--color-burnt-sienna)',
                    color: 'var(--color-burnt-sienna)',
                    background: 'transparent'
                  }}
                >
                  {withdrawingId === selectedApp.id ? 'Withdrawing Application...' : 'Withdraw Application'}
                </button>
              </div>
            )}

          </aside>
        </>
      )}

      {/* Animation pulse utility */}
      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 0.6; }
          50% { opacity: 0.3; }
        }
      `}</style>

    </CandidateLayout>
  )
}
