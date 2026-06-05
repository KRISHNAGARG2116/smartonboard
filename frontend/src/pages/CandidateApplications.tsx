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
      return { border: '1px solid var(--accent)', background: 'var(--accent-subtle)', color: 'var(--accent)', label: 'Applied' }
    } else if (s === 'screening') {
      return { border: '1px solid var(--warning)', background: 'var(--warning-bg)', color: 'var(--warning)', label: 'Reviewing' }
    } else if (s === 'interview') {
      return { border: '1px solid var(--accent)', background: 'var(--bg-subtle)', color: 'var(--accent)', label: 'Interview' }
    } else if (s === 'offer') {
      return { border: '1px solid var(--success)', background: 'var(--success-bg)', color: 'var(--success)', label: 'Offer Extended' }
    } else if (s === 'hired') {
      return { border: '1px solid var(--success)', background: 'var(--success-bg)', color: 'var(--success)', label: 'Hired' }
    } else if (s === 'rejected') {
      return { border: '1px solid var(--danger)', background: 'var(--danger-bg)', color: 'var(--danger)', label: 'Declined' }
    } else {
      return { border: '1px solid var(--border)', background: 'var(--bg-subtle)', color: 'var(--text-secondary)', label: 'Withdrawn' }
    }
  }

  return (
    <CandidateLayout>
      <div className="container" style={{ padding: 'var(--space-6) 0 var(--space-12)' }}>
        <div style={{ maxWidth: '960px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: 'var(--space-6)' }}>
          
          {/* Header Card */}
          <div className="card card__body" style={{ background: 'linear-gradient(135deg, var(--bg-subtle) 0%, var(--surface) 100%)', borderRadius: '16px' }}>
            <h3 style={{ fontSize: 'var(--text-lg)', fontWeight: 800, marginBottom: 'var(--space-2)' }}>My Applications</h3>
            <p style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-sm)', marginBottom: 0 }}>
              Track the progress and history of your submitted job applications. View historical resume and profile snapshots.
            </p>
          </div>

          {error && (
            <div className="card card__body" style={{ border: '1px solid var(--danger)', background: 'var(--danger-bg)', color: 'var(--text)', borderRadius: 'var(--radius-md)' }}>
              <strong>Error:</strong> {error}
            </div>
          )}

          {withdrawSuccess && (
            <div className="card card__body" style={{ border: '1px solid var(--success)', background: 'var(--success-bg)', color: 'var(--success)', borderRadius: 'var(--radius-md)' }}>
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
              <h4 style={{ fontSize: 'var(--text-base)', fontWeight: 700, marginBottom: 'var(--space-2)' }}>No Applications Yet</h4>
              <p style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-sm)', margin: 0 }}>
                You have not submitted any job applications yet. Go to the <Link to="/candidate/jobs" style={{ color: 'var(--accent)', fontWeight: 600 }}>Jobs Feed</Link> to apply.
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
                      borderRadius: '12px',
                      border: '1px solid var(--border)',
                      cursor: 'pointer',
                      transition: 'transform 150ms ease, border-color 150ms ease'
                    }}
                    onClick={() => {
                      setWithdrawSuccess(null)
                      setSelectedApp(app)
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.borderColor = 'var(--accent)'
                      e.currentTarget.style.transform = 'translateY(-1px)'
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.borderColor = 'var(--border)'
                      e.currentTarget.style.transform = 'translateY(0)'
                    }}
                  >
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-1)', minWidth: 0, flex: 1 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)', flexWrap: 'wrap' }}>
                        <h4 style={{ fontSize: 'var(--text-base)', fontWeight: 700, margin: 0 }}>{app.job_title}</h4>
                        <span 
                          style={{ 
                            fontSize: '10px', 
                            fontWeight: 750, 
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
                      <p style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-xs)', margin: 0 }}>
                        {app.company_name} · <strong>{app.job_department}</strong>
                      </p>
                      <span style={{ fontSize: '10px', color: 'var(--text-tertiary)' }}>
                        Applied on {new Date(app.created_at).toLocaleDateString()}
                      </span>
                    </div>

                    <div style={{ flexShrink: 0 }}>
                      <button 
                        type="button" 
                        className="btn btn--secondary btn--sm" 
                        style={{ borderRadius: '8px', padding: '8px 14px' }}
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
              background: 'rgba(0,0,0,0.4)',
              backdropFilter: 'blur(3px)',
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
              borderLeft: '1px solid var(--border)',
              display: 'flex',
              flexDirection: 'column',
              zIndex: 1000,
              boxShadow: 'var(--shadow-lg)',
              overflow: 'hidden'
            }}
          >
            {/* Drawer Header */}
            <div 
              style={{ 
                padding: 'var(--space-6)', 
                borderBottom: '1px solid var(--border)', 
                display: 'flex', 
                justifyContent: 'space-between', 
                alignItems: 'flex-start' 
              }}
            >
              <div>
                <h2 id="drawer-app-title" style={{ fontSize: 'var(--text-lg)', fontWeight: 800, letterSpacing: '-0.02em', margin: 0 }}>
                  {selectedApp.job_title}
                </h2>
                <p style={{ fontSize: 'var(--text-xs)', color: 'var(--text-secondary)', marginTop: '4px', margin: 0 }}>
                  {selectedApp.company_name} · {selectedApp.job_department}
                </p>
              </div>
              <button
                type="button"
                className="icon-btn"
                onClick={() => setSelectedApp(null)}
                style={{ 
                  border: '1px solid var(--border)', 
                  borderRadius: '50%', 
                  width: '32px', 
                  height: '32px', 
                  display: 'grid', 
                  placeItems: 'center',
                  background: 'var(--bg-subtle)'
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
                <h4 style={{ fontSize: '11px', fontWeight: 750, textTransform: 'uppercase', letterSpacing: '0.04em', color: 'var(--text-secondary)', margin: 0 }}>
                  Progress Pipeline
                </h4>
                <div 
                  style={{ 
                    padding: 'var(--space-4)', 
                    background: 'var(--bg-subtle)', 
                    borderRadius: '10px', 
                    border: '1px solid var(--border)',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '12px'
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: 'var(--text-sm)', fontWeight: 650 }}>Hiring Stage Status</span>
                    <span 
                      style={{ 
                        fontSize: '10px', 
                        fontWeight: 750, 
                        padding: '3px 8px', 
                        borderRadius: '999px',
                        ...getStatusBadgeStyle(selectedApp.status)
                      }}
                    >
                      {getStatusBadgeStyle(selectedApp.status).label}
                    </span>
                  </div>
                  <span style={{ fontSize: '10px', color: 'var(--text-tertiary)', lineHeight: 1.3 }}>
                    * Historical snapshots are immutable records of your profile fields at application time. Future profile edits will not alter this snapshot.
                  </span>
                </div>
              </div>

              {/* Frozen Snapshot Details */}
              {selectedApp.snapshot ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)' }}>
                  
                  {/* Candidate Profile fields Snapshot */}
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
                    <h4 style={{ fontSize: '11px', fontWeight: 750, textTransform: 'uppercase', letterSpacing: '0.04em', color: 'var(--text-secondary)', margin: 0 }}>
                      Profile Snapshot
                    </h4>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)', border: '1px solid var(--border)', padding: 'var(--space-4)', borderRadius: '10px' }}>
                      <div style={{ display: 'grid', gridTemplateColumns: '120px 1fr', gap: '8px', fontSize: 'var(--text-sm)' }}>
                        <span style={{ color: 'var(--text-secondary)', fontWeight: 550 }}>Full Name:</span>
                        <strong style={{ color: 'var(--text)' }}>{selectedApp.snapshot.candidate_snapshot.full_name}</strong>

                        <span style={{ color: 'var(--text-secondary)', fontWeight: 550 }}>Email Address:</span>
                        <span style={{ color: 'var(--text)', wordBreak: 'break-all' }}>{selectedApp.snapshot.candidate_snapshot.email}</span>

                        <span style={{ color: 'var(--text-secondary)', fontWeight: 550 }}>Phone Number:</span>
                        <span style={{ color: 'var(--text)' }}>{selectedApp.snapshot.candidate_snapshot.phone_number || 'N/A'}</span>

                        <span style={{ color: 'var(--text-secondary)', fontWeight: 550 }}>Location:</span>
                        <span style={{ color: 'var(--text)' }}>{selectedApp.snapshot.candidate_snapshot.location || 'N/A'}</span>
                      </div>
                    </div>
                  </div>

                  {/* Resume details Snapshot */}
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
                    <h4 style={{ fontSize: '11px', fontWeight: 750, textTransform: 'uppercase', letterSpacing: '0.04em', color: 'var(--text-secondary)', margin: 0 }}>
                      Resume Library snapshot
                    </h4>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)', border: '1px solid var(--border)', padding: 'var(--space-4)', borderRadius: '10px' }}>
                      <div>
                        <span style={{ fontSize: '10px', color: 'var(--text-tertiary)', display: 'block' }}>Submitted Resume File:</span>
                        <strong style={{ fontSize: 'var(--text-sm)' }}>📄 {selectedApp.snapshot.resume_snapshot.filename}</strong>
                      </div>
                      
                      {selectedApp.snapshot.resume_snapshot.parsed_summary && (
                        <div>
                          <span style={{ fontSize: '10px', color: 'var(--text-tertiary)', display: 'block', marginBottom: '4px' }}>Extracted Summary:</span>
                          <p style={{ fontSize: 'var(--text-xs)', color: 'var(--text-secondary)', margin: 0, lineHeight: 1.5, fontStyle: 'italic' }}>
                            "{selectedApp.snapshot.resume_snapshot.parsed_summary}"
                          </p>
                        </div>
                      )}

                      {selectedApp.snapshot.resume_snapshot.parsed_skills.length > 0 && (
                        <div>
                          <span style={{ fontSize: '10px', color: 'var(--text-tertiary)', display: 'block', marginBottom: '6px' }}>Extracted Skills:</span>
                          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                            {selectedApp.snapshot.resume_snapshot.parsed_skills.map((skill, idx) => (
                              <span 
                                key={idx} 
                                style={{ 
                                  fontSize: '10px', 
                                  padding: '2px 8px', 
                                  borderRadius: '6px', 
                                  background: 'var(--bg-subtle)', 
                                  color: 'var(--text-secondary)',
                                  border: '1px solid var(--border)'
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
                <div style={{ textAlign: 'center', color: 'var(--text-tertiary)', fontSize: 'var(--text-xs)', padding: 'var(--space-6) 0' }}>
                  No historical snapshot metadata found for this application.
                </div>
              )}

            </div>

            {/* Drawer Footer Withdrawal Action Panel */}
            {selectedApp.status.toLowerCase() !== 'withdrawn' && selectedApp.status.toLowerCase() !== 'rejected' && (
              <div 
                style={{ 
                  padding: 'var(--space-6)', 
                  borderTop: '1px solid var(--border)', 
                  background: 'var(--bg-subtle)'
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
                    borderRadius: '10px', 
                    fontWeight: 700,
                    borderColor: 'var(--danger)',
                    color: 'var(--danger)',
                    background: 'var(--surface)'
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
