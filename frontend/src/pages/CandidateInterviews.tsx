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
          <div className="card card__body" style={{ background: 'transparent', border: '1px dashed var(--color-cork-shadow)', borderRadius: '12px' }}>
            <h3 style={{ fontSize: '29px', fontWeight: 500, letterSpacing: '-0.02em', marginBottom: 'var(--space-2)', lineHeight: 1.09, color: 'var(--text)' }}>My Interviews</h3>
            <p style={{ color: 'var(--color-grey-brown)', fontSize: '14px', lineHeight: 1.33, marginBottom: 0 }}>
              Review your upcoming and past structured interview slots. Join video meetings or reschedule confirmed bookings.
            </p>
          </div>

          {error && (
            <div className="card card__body" style={{ border: '1px solid var(--color-burnt-sienna)', background: 'transparent', color: 'var(--color-burnt-sienna)', borderRadius: '0px' }}>
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
            <div className="card card__body" style={{ textAlign: 'center', padding: 'var(--space-12) var(--space-6)', background: 'transparent', border: '1px dashed var(--color-cork-shadow)', borderRadius: '12px' }}>
              <span style={{ fontSize: '48px', display: 'block', marginBottom: 'var(--space-4)' }}>📅</span>
              <h4 style={{ fontSize: '18px', fontWeight: 500, color: 'var(--text)', marginBottom: 'var(--space-2)' }}>No Interviews Scheduled</h4>
              <p style={{ color: 'var(--color-grey-brown)', fontSize: '14px', margin: 0 }}>
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
                      border: '1px dashed var(--color-cork-shadow)',
                      background: 'transparent',
                      opacity: isCancelled ? 0.6 : 1
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 'var(--space-2)' }}>
                      <div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)', flexWrap: 'wrap' }}>
                          <h4 style={{ fontSize: '15px', fontWeight: 500, color: 'var(--text)', margin: 0 }}>{iv.title}</h4>
                          <span 
                            style={{ 
                              fontSize: '10px', 
                              fontWeight: 500, 
                              padding: '2px 8px', 
                              borderRadius: '999px',
                              background: 'transparent',
                              color: isCancelled ? 'var(--color-burnt-sienna)' : isPast ? 'var(--color-grey-brown)' : 'var(--text)',
                              border: isCancelled ? '1px solid var(--color-burnt-sienna)' : isPast ? '1px solid var(--color-cork-shadow)' : '1px solid var(--color-warm-cream)'
                            }}
                          >
                            {isCancelled ? 'Cancelled' : isPast ? 'Past' : 'Confirmed'}
                          </span>
                        </div>
                        <p style={{ color: 'var(--color-grey-brown)', fontSize: '12px', marginTop: '2px', margin: 0 }}>
                          {iv.company_name} · Position: <strong>{iv.job_title}</strong>
                        </p>
                      </div>
                      
                      <div style={{ fontSize: '12px', color: 'var(--color-grey-brown)', textAlign: 'right' }}>
                        <div>📅 <strong style={{ color: 'var(--text)', fontWeight: 500 }}>{new Date(iv.scheduled_at).toLocaleString()}</strong></div>
                        <div style={{ marginTop: '2px' }}>⏱️ Duration: {iv.duration_minutes} min</div>
                      </div>
                    </div>

                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderTop: '1px dashed var(--color-cork-shadow)', paddingTop: 'var(--space-3)', marginTop: 'var(--space-1)', flexWrap: 'wrap', gap: 'var(--space-2)' }}>
                      <div style={{ fontSize: '12px', color: 'var(--color-grey-brown)' }}>
                        Interviewer: <strong style={{ color: 'var(--text)', fontWeight: 500 }}>{iv.interviewer_name}</strong>
                      </div>
                      
                      <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
                        {iv.video_link && isConfirmed && !isPast && (
                          <a 
                            href={iv.video_link} 
                            target="_blank" 
                            rel="noopener noreferrer"
                            className="btn btn--primary btn--sm"
                            style={{ borderRadius: '36px', background: 'var(--color-dark-cork)', color: 'var(--text)', border: 'none', padding: '6px 12px', fontSize: '12px', boxShadow: 'none' }}
                          >
                            💻 Join Video Call
                          </a>
                        )}

                        {iv.slot && isConfirmed && !isPast && (
                          <>
                            <button
                              type="button"
                              className="btn btn--secondary btn--sm"
                              style={{ borderRadius: '22.5px', border: '1px solid var(--color-warm-cream)', background: 'transparent', color: 'var(--text)', padding: '6px 12px', fontSize: '12px' }}
                              onClick={() => setSelectedIv(iv)}
                            >
                              Reschedule
                            </button>
                            <button
                              type="button"
                              className="btn btn--ghost btn--sm"
                              style={{ borderRadius: '22.5px', border: '1px solid var(--color-burnt-sienna)', background: 'transparent', padding: '6px 12px', fontSize: '12px', color: 'var(--color-burnt-sienna)' }}
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
              background: 'rgba(16,9,4,0.7)',
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
              background: 'var(--color-studio-black)',
              border: '1px solid var(--color-warm-cream)',
              borderRadius: '12px',
              padding: 'var(--space-6)',
              zIndex: 1000,
              boxShadow: 'none',
              display: 'flex',
              flexDirection: 'column',
              gap: 'var(--space-4)'
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div>
                <h3 style={{ fontSize: '18px', fontWeight: 500, color: 'var(--text)', margin: 0 }}>Reschedule Interview</h3>
                <p style={{ fontSize: '12px', color: 'var(--color-grey-brown)', marginTop: '2px', margin: 0 }}>
                  {selectedIv.title} with {selectedIv.interviewer_name}
                </p>
              </div>
              <button 
                type="button" 
                onClick={() => setSelectedIv(null)}
                style={{ fontSize: '18px', padding: '4px', cursor: 'pointer', background: 'transparent', border: 'none', color: 'var(--color-grey-brown)' }}
              >
                ✕
              </button>
            </div>

            {rescheduleError && (
              <div style={{ background: 'transparent', color: 'var(--color-burnt-sienna)', padding: 'var(--space-3)', borderRadius: '0px', fontSize: '12px', border: '1px solid var(--color-burnt-sienna)' }}>
                <strong>Reschedule Failed:</strong> {rescheduleError}
              </div>
            )}

            {rescheduleSuccess && (
              <div style={{ background: 'transparent', color: 'var(--text)', padding: 'var(--space-3)', borderRadius: '0px', fontSize: '12px', border: '1px solid var(--color-warm-cream)', textAlign: 'center' }}>
                {rescheduleSuccess}
              </div>
            )}

            <form onSubmit={handleRescheduleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)', marginTop: 'var(--space-2)' }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                <label htmlFor="new-start-time" style={{ fontSize: '10px', textTransform: 'uppercase', fontWeight: 500, color: 'var(--color-grey-brown)', letterSpacing: '0.05em' }}>
                  Choose New Date & Time:
                </label>
                <input
                  id="new-start-time"
                  type="datetime-local"
                  required
                  value={newStartTime}
                  onChange={(e) => setNewStartTime(e.target.value)}
                  style={{
                    padding: '10px 0px',
                    borderRadius: '0px',
                    border: 'none',
                    borderBottom: '1px solid var(--color-warm-cream)',
                    background: 'transparent',
                    color: 'var(--text)',
                    fontSize: '15px',
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
                  style={{ flex: 1, borderRadius: '22.5px', border: '1px solid var(--color-warm-cream)', background: 'transparent', color: 'var(--text)' }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn btn--primary"
                  disabled={rescheduling || !newStartTime}
                  style={{ 
                    flex: 1, 
                    borderRadius: '36px',
                    background: 'var(--color-dark-cork)',
                    color: 'var(--text)',
                    fontWeight: 500,
                    border: 'none',
                    boxShadow: 'none'
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
