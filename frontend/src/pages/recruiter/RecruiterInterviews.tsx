import { useState, useEffect, useCallback } from 'react'
import AppLayout from '../../components/AppLayout'
import { useAuth } from '../../context/AuthContext'
import { 
  fetchApplications, 
  fetchInterviews, 
  createInterview, 
  updateInterview, 
  type Application 
} from '../../api'
import SteepCard from '../../components/design-system/SteepCard'
import SteepButton from '../../components/design-system/SteepButton'
import SteepInput from '../../components/design-system/SteepInput'
import SteepBadge from '../../components/design-system/SteepBadge'
import EmptyState from '../../components/EmptyState'

interface InterviewItem {
  id: string
  application_id: string
  candidate_name: string
  job_title: string
  interviewer_id: string
  title: string
  stage: string
  scheduled_at: string
  duration_minutes: number
  video_link: string | null
  is_cancelled: boolean
}

export default function RecruiterInterviews() {
  const { user } = useAuth()
  const [applications, setApplications] = useState<Application[]>([])
  const [interviews, setInterviews] = useState<InterviewItem[]>([])
  const [loading, setLoading] = useState(true)

  // Modal states
  const [isScheduleOpen, setIsScheduleOpen] = useState(false)
  const [isRescheduleOpen, setIsRescheduleOpen] = useState(false)
  const [selectedInterview, setSelectedInterview] = useState<InterviewItem | null>(null)

  // Form states (Schedule)
  const [selectedAppId, setSelectedAppId] = useState('')
  const [title, setTitle] = useState('Technical Screening Panel')
  const [stage, setStage] = useState('SCREENING')
  const [scheduledAt, setScheduledAt] = useState('')
  const [duration, setDuration] = useState('45')
  const [videoLink, setVideoLink] = useState('https://meet.google.com/smartonboard-meet')
  const [submitting, setSubmitting] = useState(false)

  // Form states (Reschedule)
  const [newScheduledAt, setNewScheduledAt] = useState('')
  const [reschedulingSubmitting, setReschedulingSubmitting] = useState(false)

  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const apps = await fetchApplications()
      setApplications(apps)

      // Fetch interviews for each application in parallel
      const interviewPromises = apps.map(async (app) => {
        try {
          const ivList = await fetchInterviews(app.id)
          return ivList.map((iv: any) => ({
            id: iv.id,
            application_id: app.id,
            candidate_name: app.candidate?.full_name || 'Candidate',
            job_title: app.job?.title || 'General Opening',
            interviewer_id: iv.interviewer_id,
            title: iv.title,
            stage: iv.stage,
            scheduled_at: iv.scheduled_at,
            duration_minutes: iv.duration_minutes,
            video_link: iv.video_link,
            is_cancelled: iv.is_cancelled
          }))
        } catch {
          return []
        }
      })

      const results = await Promise.all(interviewPromises)
      const allInterviews: InterviewItem[] = results.flat()
      
      // Sort chronologically
      allInterviews.sort((a, b) => new Date(a.scheduled_at).getTime() - new Date(b.scheduled_at).getTime())
      setInterviews(allInterviews)
    } catch (err) {
      console.error('Error coordinating interviews:', err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadData()
  }, [loadData])

  const handleScheduleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedAppId || !scheduledAt) return
    setSubmitting(true)
    try {
      await createInterview(selectedAppId, {
        interviewer_id: user?.id || '',
        title,
        stage,
        scheduled_at: new Date(scheduledAt).toISOString(),
        duration_minutes: parseInt(duration, 10),
        video_link: videoLink || null
      })
      alert('Interview panel scheduled successfully!')
      setIsScheduleOpen(false)
      setSelectedAppId('')
      setScheduledAt('')
      loadData()
    } catch (err) {
      alert('Error scheduling interview. Check slot availability or user roles.')
    } finally {
      setSubmitting(false)
    }
  }

  const handleRescheduleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedInterview || !newScheduledAt) return
    setReschedulingSubmitting(true)
    try {
      await updateInterview(selectedInterview.application_id, selectedInterview.id, {
        scheduled_at: new Date(newScheduledAt).toISOString()
      })
      alert('Interview successfully rescheduled!')
      setIsRescheduleOpen(false)
      setSelectedInterview(null)
      setNewScheduledAt('')
      loadData()
    } catch (err) {
      alert('Failed to reschedule interview. Verify resource calendars.')
    } finally {
      setReschedulingSubmitting(false)
    }
  }

  const handleCancelInterview = async (iv: InterviewItem) => {
    if (!confirm('Are you sure you want to cancel this interview?')) return
    try {
      await updateInterview(iv.application_id, iv.id, { is_cancelled: true })
      alert('Interview cancelled successfully.')
      loadData()
    } catch (err) {
      alert('Error cancelling interview.')
    }
  }

  return (
    <AppLayout>
      <div className="container" style={{ padding: 'var(--spacing-32) 0 var(--spacing-48)' }}>
        {/* Header */}
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          borderBottom: '1px solid var(--border)',
          paddingBottom: 'var(--spacing-24)',
          marginBottom: 'var(--spacing-24)'
        }}>
          <div>
            <span style={{ fontSize: 'var(--text-caption)', fontWeight: 550, color: 'var(--color-ash)', letterSpacing: '0.05em', textTransform: 'uppercase' }}>
              Talent Coordination
            </span>
            <h1 className="font-signifier" style={{ fontSize: 'var(--text-heading-sm)', fontWeight: 500, color: 'var(--color-ink)', margin: '4px 0 0', lineHeight: 1.09 }}>
              Interviews Calendar
            </h1>
          </div>
          <SteepButton 
            onClick={() => setIsScheduleOpen(true)}
            variant="primary"
          >
            Schedule Panel
          </SteepButton>
        </div>

        {loading ? (
          <div style={{ padding: 'var(--spacing-48) 0', textAlign: 'center', color: 'var(--color-ash)' }}>
            Loading interview calendar...
          </div>
        ) : interviews.length === 0 ? (
          <EmptyState
            type="interviews"
            title="No interviews scheduled"
            description="There are currently no active interview panels. Select a candidate to schedule their evaluation."
            actionLabel="Schedule Interview Panel"
            onAction={() => setIsScheduleOpen(true)}
          />
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-16)' }}>
            {interviews.map((iv) => (
              <SteepCard 
                key={iv.id}
                style={{
                  padding: 'var(--spacing-16) var(--spacing-24)',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  opacity: iv.is_cancelled ? 0.6 : 1
                }}
              >
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <h3 style={{ fontSize: 'var(--text-body-lg)', fontWeight: 500, color: 'var(--color-ink)', margin: 0 }}>
                      {iv.candidate_name}
                    </h3>
                    <SteepBadge variant={iv.is_cancelled ? 'danger' : 'interview'}>
                      {iv.is_cancelled ? 'Cancelled' : iv.stage}
                    </SteepBadge>
                  </div>
                  <div style={{ display: 'flex', gap: 12, marginTop: 6, fontSize: 'var(--text-caption)', color: 'var(--color-ash)', alignItems: 'center' }}>
                    <span>Role: {iv.job_title}</span>
                    <span>&bull;</span>
                    <span>Title: {iv.title}</span>
                    <span>&bull;</span>
                    <span>Scheduled: {new Date(iv.scheduled_at).toLocaleString()} ({iv.duration_minutes}m)</span>
                    {iv.video_link && !iv.is_cancelled && (
                      <>
                        <span>&bull;</span>
                        <a href={iv.video_link} target="_blank" rel="noreferrer" style={{ color: 'var(--color-rust)', textDecoration: 'underline' }}>
                          Join Meeting
                        </a>
                      </>
                    )}
                  </div>
                </div>
                
                {!iv.is_cancelled && (
                  <div style={{ display: 'flex', gap: '8px' }}>
                    <SteepButton
                      variant="secondary"
                      size="sm"
                      onClick={() => {
                        setSelectedInterview(iv)
                        setNewScheduledAt(iv.scheduled_at.slice(0, 16))
                        setIsRescheduleOpen(true)
                      }}
                    >
                      Reschedule
                    </SteepButton>
                    <SteepButton
                      variant="secondary"
                      size="sm"
                      onClick={() => handleCancelInterview(iv)}
                    >
                      Cancel
                    </SteepButton>
                  </div>
                )}
              </SteepCard>
            ))}
          </div>
        )}

        {/* Schedule Modal */}
        {isScheduleOpen && (
          <div style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(93, 42, 26, 0.4)',
            backdropFilter: 'blur(4px)',
            display: 'grid',
            placeItems: 'center',
            zIndex: 250,
            padding: 24
          }}>
            <div style={{ maxWidth: 480, width: '100%' }}>
              <SteepCard style={{ padding: 32 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
                  <h2 className="font-signifier" style={{ fontSize: 24, fontWeight: 500, margin: 0, color: 'var(--color-ink)' }}>
                    Schedule Interview Panel
                  </h2>
                  <SteepButton variant="ghost" onClick={() => setIsScheduleOpen(false)} style={{ padding: 4 }}>✕</SteepButton>
                </div>

                <form onSubmit={handleScheduleSubmit}>
                  <SteepInput 
                    id="sched-candidate"
                    label="Select Candidate"
                    select
                    options={[
                      { value: '', label: 'Choose active candidate...' },
                      ...applications.filter(a => a.status !== 'hired' && a.status !== 'rejected').map(a => ({
                        value: a.id,
                        label: `${a.candidate?.full_name} — ${a.job?.title}`
                      }))
                    ]}
                    value={selectedAppId}
                    onChange={e => setSelectedAppId(e.target.value)}
                    required
                  />

                  <SteepInput 
                    id="sched-title"
                    label="Interview Title"
                    value={title}
                    onChange={e => setTitle(e.target.value)}
                    required
                  />

                  <SteepInput 
                    id="sched-stage"
                    label="Hiring Stage"
                    select
                    options={['SCREENING', 'INTERVIEW', 'COMMITTEE'].map(s => ({ value: s, label: s }))}
                    value={stage}
                    onChange={e => setStage(e.target.value)}
                    required
                  />

                  <SteepInput 
                    id="sched-time"
                    type="datetime-local"
                    label="Date & Time"
                    value={scheduledAt}
                    onChange={e => setScheduledAt(e.target.value)}
                    required
                  />

                  <SteepInput 
                    id="sched-duration"
                    label="Duration (minutes)"
                    select
                    options={['15', '30', '45', '60', '90'].map(m => ({ value: m, label: `${m} Minutes` }))}
                    value={duration}
                    onChange={e => setDuration(e.target.value)}
                    required
                  />

                  <SteepInput 
                    id="sched-link"
                    label="Video Link"
                    value={videoLink}
                    onChange={e => setVideoLink(e.target.value)}
                    placeholder="https://meet.google.com/..."
                  />

                  <div style={{ display: 'flex', gap: 12, justifyContent: 'flex-end', marginTop: 24 }}>
                    <SteepButton 
                      type="button" 
                      onClick={() => setIsScheduleOpen(false)}
                      variant="secondary" 
                    >
                      Cancel
                    </SteepButton>
                    <SteepButton 
                      type="submit" 
                      disabled={submitting || !selectedAppId}
                      variant="primary" 
                    >
                      {submitting ? 'Scheduling...' : 'Schedule Panel'}
                    </SteepButton>
                  </div>
                </form>
              </SteepCard>
            </div>
          </div>
        )}

        {/* Reschedule Modal */}
        {isRescheduleOpen && (
          <div style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(93, 42, 26, 0.4)',
            backdropFilter: 'blur(4px)',
            display: 'grid',
            placeItems: 'center',
            zIndex: 250,
            padding: 24
          }}>
            <div style={{ maxWidth: 480, width: '100%' }}>
              <SteepCard style={{ padding: 32 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
                  <h2 className="font-signifier" style={{ fontSize: 24, fontWeight: 500, margin: 0, color: 'var(--color-ink)' }}>
                    Reschedule Interview
                  </h2>
                  <SteepButton variant="ghost" onClick={() => { setIsRescheduleOpen(false); setSelectedInterview(null); }} style={{ padding: 4 }}>✕</SteepButton>
                </div>

                <form onSubmit={handleRescheduleSubmit}>
                  <SteepInput 
                    id="resched-time"
                    type="datetime-local"
                    label="New Date & Time"
                    value={newScheduledAt}
                    onChange={e => setNewScheduledAt(e.target.value)}
                    required
                  />

                  <div style={{ display: 'flex', gap: 12, justifyContent: 'flex-end', marginTop: 24 }}>
                    <SteepButton 
                      type="button" 
                      onClick={() => { setIsRescheduleOpen(false); setSelectedInterview(null); }}
                      variant="secondary" 
                    >
                      Cancel
                    </SteepButton>
                    <SteepButton 
                      type="submit" 
                      disabled={reschedulingSubmitting || !newScheduledAt}
                      variant="primary" 
                    >
                      {reschedulingSubmitting ? 'Rescheduling...' : 'Reschedule'}
                    </SteepButton>
                  </div>
                </form>
              </SteepCard>
            </div>
          </div>
        )}

      </div>
    </AppLayout>
  )
}
