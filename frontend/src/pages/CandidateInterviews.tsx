import { useState, useEffect } from 'react'
import CandidateLayout from '../components/CandidateLayout'
import {
  fetchMyInterviews,
  cancelCandidateBooking,
  rescheduleCandidateBooking,
  type CandidateInterviewItem
} from '../api'

export default function CandidateInterviews() {
  const [interviews, setInterviews] = useState<CandidateInterviewItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Reschedule / Cancellation state
  const [selectedIv, setSelectedIv] = useState<CandidateInterviewItem | null>(null)
  const [newStartTime, setNewStartTime] = useState('')
  const [rescheduling, setRescheduling] = useState(false)
  const [rescheduleError, setRescheduleError] = useState<string | null>(null)
  const [rescheduleSuccess, setRescheduleSuccess] = useState<string | null>(null)
  const [cancellingId, setCancellingId] = useState<string | null>(null)

  const loadInterviews = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchMyInterviews()
      setInterviews(data)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to retrieve interviews. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadInterviews()
  }, [])

  const handleCancel = async (slotId: string) => {
    if (!window.confirm("Are you sure you want to cancel this interview booking slot? The interviewer will be notified.")) {
      return
    }
    setCancellingId(slotId)
    try {
      await cancelCandidateBooking(slotId)
      alert("Interview cancelled successfully.")
      await loadInterviews()
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to cancel booking. Please try again.')
    } finally {
      setCancellingId(null)
    }
  }

  const handleRescheduleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedIv || !selectedIv.slot || !newStartTime) return
    
    setRescheduling(true)
    setRescheduleError(null)
    setRescheduleSuccess(null)
    
    try {
      await rescheduleCandidateBooking(selectedIv.slot.id, newStartTime)
      setRescheduleSuccess("Interview rescheduled successfully.")
      // Reload lists
      await loadInterviews()
      // Close modal after delay
      setTimeout(() => {
        setSelectedIv(null)
        setNewStartTime('')
        setRescheduleSuccess(null)
      }, 1500)
    } catch (err: any) {
      setRescheduleError(err.response?.data?.detail || 'Failed to reschedule interview. Overlapping reservation may exist.')
    } finally {
      setRescheduling(false)
    }
  }

  return (
    <CandidateLayout>
      <div className="container" style={{ padding: 'var(--space-6) 0 var(--space-12)' }}>
        <div style={{ maxWidth: '960px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: 'var(--space-6)' }}>
          
          {/* Header Card */}
          <div className="card card__body" style={{ background: 'linear-gradient(135deg, var(--bg-subtle) 0%, var(--surface) 100%)', borderRadius: '16px' }}>
            <h3 style={{ fontSize: 'var(--text-lg)', fontWeight: 800, marginBottom: 'var(--space-2)' }}>My Interviews</h3>
            <p style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-sm)', marginBottom: 0 }}>
              Review your upcoming and past structured interview slots. Join video meetings or reschedule confirmed bookings.
            </p>
          </div>

          {error && (
            <div className="card card__body" style={{ border: '1px solid var(--danger)', background: 'var(--danger-bg)', color: 'var(--text)', borderRadius: 'var(--radius-md)' }}>
              <strong>Error:</strong> {error}
            </div>
          )}

          {/* Interviews List */}
          {loading ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
              {[1, 2].map(i => (
                <div key={i} className="card card__body" style={{ height: '110px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', opacity: 0.6, animation: 'pulse 1.5s infinite' }}>
                  <div style={{ width: '35%', height: '16px', background: 'var(--border)', borderRadius: '4px' }}></div>
                  <div style={{ width: '55%', height: '12px', background: 'var(--border)', borderRadius: '4px' }}></div>
                </div>
              ))}
            </div>
          ) : interviews.length === 0 ? (
            <div className="card card__body" style={{ textAlign: 'center', padding: 'var(--space-12) var(--space-6)' }}>
              <span style={{ fontSize: '48px', display: 'block', marginBottom: 'var(--space-4)' }}>📅</span>
              <h4 style={{ fontSize: 'var(--text-base)', fontWeight: 700, marginBottom: 'var(--space-2)' }}>No Interviews Scheduled</h4>
              <p style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-sm)', margin: 0 }}>
                Interviews will appear here once scheduled by recruiters or booked via scheduling links.
              </p>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
              {interviews.map((iv) => {
                const isConfirmed = iv.slot && iv.slot.status === 'confirmed' && !iv.is_cancelled
                const isCancelled = iv.is_cancelled || (iv.slot && iv.slot.status === 'cancelled')
                const isPast = new Date(iv.scheduled_at) < new Date()

                return (
                  <div 
                    key={iv.id} 
                    className="card card__body"
                    style={{ 
                      display: 'flex', 
                      flexDirection: 'column',
                      gap: 'var(--space-3)',
                      borderRadius: '12px',
                      border: '1px solid var(--border)',
                      opacity: isCancelled ? 0.6 : 1
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 'var(--space-2)' }}>
                      <div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)', flexWrap: 'wrap' }}>
                          <h4 style={{ fontSize: 'var(--text-base)', fontWeight: 700, margin: 0 }}>{iv.title}</h4>
                          <span 
                            style={{ 
                              fontSize: '10px', 
                              fontWeight: 750, 
                              padding: '2px 8px', 
                              borderRadius: '999px',
                              background: isCancelled ? 'var(--danger-bg)' : isPast ? 'var(--bg-subtle)' : 'var(--success-bg)',
                              color: isCancelled ? 'var(--danger)' : isPast ? 'var(--text-secondary)' : 'var(--success)',
                              border: isCancelled ? '1px solid var(--danger)' : isPast ? '1px solid var(--border)' : '1px solid var(--success)'
                            }}
                          >
                            {isCancelled ? 'Cancelled' : isPast ? 'Past' : 'Confirmed'}
                          </span>
                        </div>
                        <p style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-xs)', marginTop: '2px', margin: 0 }}>
                          {iv.company_name} · Position: <strong>{iv.job_title}</strong>
                        </p>
                      </div>
                      
                      <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-secondary)', textAlign: 'right' }}>
                        <div>📅 <strong>{new Date(iv.scheduled_at).toLocaleString()}</strong></div>
                        <div style={{ marginTop: '2px' }}>⏱️ Duration: {iv.duration_minutes} min</div>
                      </div>
                    </div>

                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderTop: '1px solid var(--border)', paddingTop: 'var(--space-3)', marginTop: 'var(--space-1)', flexWrap: 'wrap', gap: 'var(--space-2)' }}>
                      <div style={{ fontSize: 'var(--text-xs)' }}>
                        Interviewer: <strong>{iv.interviewer_name}</strong>
                      </div>
                      
                      <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
                        {iv.video_link && isConfirmed && !isPast && (
                          <a 
                            href={iv.video_link} 
                            target="_blank" 
                            rel="noopener noreferrer"
                            className="btn btn--primary btn--sm"
                            style={{ borderRadius: '8px', padding: '6px 12px', fontSize: 'var(--text-xs)' }}
                          >
                            💻 Join Video Call
                          </a>
                        )}

                        {iv.slot && isConfirmed && !isPast && (
                          <>
                            <button
                              type="button"
                              className="btn btn--secondary btn--sm"
                              style={{ borderRadius: '8px', padding: '6px 12px', fontSize: 'var(--text-xs)' }}
                              onClick={() => setSelectedIv(iv)}
                            >
                              Reschedule
                            </button>
                            <button
                              type="button"
                              className="btn btn--ghost btn--sm"
                              style={{ borderRadius: '8px', padding: '6px 12px', fontSize: 'var(--text-xs)', color: 'var(--danger)' }}
                              disabled={cancellingId === iv.slot.id}
                              onClick={() => handleCancel(iv.slot!.id)}
                            >
                              {cancellingId === iv.slot.id ? 'Cancelling...' : 'Cancel'}
                            </button>
                          </>
                        )}
                      </div>
                    </div>

                  </div>
                )
              })}
            </div>
          )}

        </div>
      </div>

      {/* Reschedule Modal Overlay */}
      {selectedIv && selectedIv.slot && (
        <>
          <div 
            onClick={() => setSelectedIv(null)}
            style={{
              position: 'fixed',
              inset: 0,
              background: 'rgba(0,0,0,0.4)',
              backdropFilter: 'blur(3px)',
              zIndex: 999
            }}
          />
          <div
            style={{
              position: 'fixed',
              top: '50%',
              left: '50%',
              transform: 'translate(-50%, -50%)',
              width: 'min(460px, 90vw)',
              background: 'var(--surface)',
              border: '1px solid var(--border)',
              borderRadius: '16px',
              padding: 'var(--space-6)',
              zIndex: 1000,
              boxShadow: 'var(--shadow-lg)',
              display: 'flex',
              flexDirection: 'column',
              gap: 'var(--space-4)'
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div>
                <h3 style={{ fontSize: 'var(--text-base)', fontWeight: 800, margin: 0 }}>Reschedule Interview</h3>
                <p style={{ fontSize: 'var(--text-xs)', color: 'var(--text-secondary)', marginTop: '2px', margin: 0 }}>
                  {selectedIv.title} with {selectedIv.interviewer_name}
                </p>
              </div>
              <button 
                type="button" 
                onClick={() => setSelectedIv(null)}
                style={{ fontSize: '18px', padding: '4px', cursor: 'pointer', color: 'var(--text-secondary)' }}
              >
                ✕
              </button>
            </div>

            {rescheduleError && (
              <div style={{ background: 'var(--danger-bg)', color: 'var(--danger)', padding: 'var(--space-3)', borderRadius: '8px', fontSize: 'var(--text-xs)', border: '1px solid var(--danger)' }}>
                <strong>Reschedule Failed:</strong> {rescheduleError}
              </div>
            )}

            {rescheduleSuccess && (
              <div style={{ background: 'var(--success-bg)', color: 'var(--success)', padding: 'var(--space-3)', borderRadius: '8px', fontSize: 'var(--text-xs)', border: '1px solid var(--success)', textAlign: 'center' }}>
                {rescheduleSuccess}
              </div>
            )}

            <form onSubmit={handleRescheduleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)', marginTop: 'var(--space-2)' }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                <label htmlFor="new-start-time" style={{ fontSize: '11px', fontWeight: 700, color: 'var(--text-secondary)' }}>
                  Choose New Date & Time:
                </label>
                <input
                  id="new-start-time"
                  type="datetime-local"
                  required
                  value={newStartTime}
                  onChange={(e) => setNewStartTime(e.target.value)}
                  style={{
                    padding: '10px 14px',
                    borderRadius: '10px',
                    border: '1px solid var(--border)',
                    background: 'var(--bg-subtle)',
                    color: 'var(--text)',
                    fontSize: 'var(--text-sm)',
                    fontFamily: 'inherit',
                    width: '100%'
                  }}
                />
              </div>

              <div style={{ display: 'flex', gap: 'var(--space-3)', marginTop: 'var(--space-2)' }}>
                <button
                  type="button"
                  className="btn btn--secondary"
                  onClick={() => setSelectedIv(null)}
                  style={{ flex: 1, borderRadius: '10px' }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn btn--primary"
                  disabled={rescheduling || !newStartTime}
                  style={{ 
                    flex: 1, 
                    borderRadius: '10px',
                    background: 'linear-gradient(135deg, var(--accent) 0%, var(--accent-hover) 100%)',
                    color: 'var(--text-inverse)',
                    fontWeight: 700
                  }}
                >
                  {rescheduling ? 'Rescheduling...' : 'Confirm'}
                </button>
              </div>
            </form>

          </div>
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
