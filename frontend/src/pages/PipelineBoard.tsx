import { useState, useEffect, useMemo, useCallback } from 'react'
import { motion, type Variants } from 'framer-motion'
import AppLayout from '../components/AppLayout'
import CandidateDrawer from '../components/CandidateDrawer'
import { 
  fetchApplications, 
  fetchJobs, 
  fetchJobStages, 
  moveApplicationStage, 
  getVerificationStatus, 
  type Application 
} from '../api'
import SteepCard from '../components/design-system/SteepCard'
import SteepButton from '../components/design-system/SteepButton'
import SteepBadge from '../components/design-system/SteepBadge'
import MatchScoreBadge from '../components/MatchScoreBadge'

const cardVariants: Variants = {
  hidden: { opacity: 0, y: 8 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: {
      delay: Math.min(i * 0.04, 0.3),
      duration: 0.25,
      ease: 'easeOut'
    }
  })
}

export default function PipelineBoard() {
  const [jobs, setJobs] = useState<any[]>([])
  const [selectedJobId, setSelectedJobId] = useState<string>('')
  const [stages, setStages] = useState<any[]>([])
  const [applications, setApplications] = useState<Application[]>([])
  const [loading, setLoading] = useState(true)
  const [stagesLoading, setStagesLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Drawer candidate state
  const [selectedApp, setSelectedApp] = useState<Application | null>(null)
  const [drawerTab, setDrawerTab] = useState<'overview' | 'screening' | 'interviews' | 'offers' | 'timeline'>('overview')

  // Drag over column state highlighting
  const [dragOverColumnId, setDragOverColumnId] = useState<string | null>(null)

  // 1. Fetch all active jobs on mount
  useEffect(() => {
    async function loadJobs() {
      try {
        const activeJobs = await fetchJobs('open')
        setJobs(activeJobs)
        if (activeJobs.length > 0) {
          setSelectedJobId(activeJobs[0].id)
        } else {
          setLoading(false)
        }
      } catch (err) {
        console.error('Error fetching jobs:', err)
        setError('Failed to load jobs. Please refresh the page.')
        setLoading(false)
      }
    }
    loadJobs()
  }, [])

  // 2. Fetch stages and applications for the selected job
  const loadJobData = useCallback(async (jobId: string) => {
    if (!jobId) return
    setStagesLoading(true)
    setError(null)
    try {
      // Fetch dynamic stage definitions
      const stageList = await fetchJobStages(jobId)
      setStages(stageList)

      // Fetch applications
      const appList = await fetchApplications(jobId)

      // Enrich applications with verification status
      const enrichedApps = await Promise.all(
        appList.map(async (app) => {
          if (app.candidate?.email) {
            try {
              const statusData = await getVerificationStatus(app.candidate.email)
              return {
                ...app,
                candidate: {
                  ...app.candidate,
                  email_verified: statusData.email_verified,
                  phone_verified: statusData.phone_verified,
                  verified: !statusData.verification_required,
                }
              }
            } catch {
              return app
            }
          }
          return app
        })
      )
      setApplications(enrichedApps)
    } catch (err) {
      console.error('Error loading job pipeline details:', err)
      setError('Failed to load hiring pipeline stages.')
    } finally {
      setStagesLoading(false)
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (selectedJobId) {
      loadJobData(selectedJobId)
    }
  }, [selectedJobId, loadJobData])

  // --- Dynamic calculations per stage column ---
  const columnMetrics = useMemo(() => {
    const metrics: Record<string, { count: number; avgScore: number; avgDays: number; hasBreach: boolean }> = {}

    stages.forEach((stage) => {
      const stageApps = applications.filter((app) => app.current_stage_id === stage.id)
      const count = stageApps.length
      
      let totalScore = 0
      let totalDays = 0
      let hasBreach = false

      stageApps.forEach((app) => {
        totalScore += app.match_score || 0
        const diffTime = Math.abs(new Date(app.updated_at).getTime() - new Date(app.created_at).getTime())
        const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24))
        totalDays += diffDays

        // SLA Breach calculation
        if (stage.sla_enabled && stage.sla_hours) {
          if (diffDays * 24 > stage.sla_hours) {
            hasBreach = true
          }
        }
      })

      const avgScore = count > 0 ? Math.round(totalScore / count) : 0
      const avgDays = count > 0 ? Math.round(totalDays / count) : 0

      metrics[stage.id] = { count, avgScore, avgDays, hasBreach }
    })

    return metrics
  }, [stages, applications])

  // --- HTML5 Drag and Drop handlers ---
  const handleDragStart = (e: React.DragEvent, appId: string) => {
    e.dataTransfer.setData('text/plain', appId)
    e.dataTransfer.effectAllowed = 'move'
  }

  const handleDragOver = (e: React.DragEvent, stageId: string) => {
    e.preventDefault()
    setDragOverColumnId(stageId)
  }

  const handleDragLeave = () => {
    setDragOverColumnId(null)
  }

  const handleDrop = async (e: React.DragEvent, targetStageId: string) => {
    e.preventDefault()
    setDragOverColumnId(null)
    const appId = e.dataTransfer.getData('text/plain')
    if (!appId) return

    const app = applications.find((a) => a.id === appId)
    if (!app) return

    const originalStageId = app.current_stage_id
    if (originalStageId === targetStageId) return

    // Optimistic UI Update: Move stage locally
    setApplications((prev) =>
      prev.map((a) => (a.id === appId ? { ...a, current_stage_id: targetStageId, updated_at: new Date().toISOString() } : a))
    )

    try {
      await moveApplicationStage(appId, {
        target_stage_id: targetStageId,
        client_updated_at: app.updated_at
      })
    } catch (err: any) {
      // Revert card position on failure
      setApplications((prev) =>
        prev.map((a) => (a.id === appId ? { ...a, current_stage_id: originalStageId } : a))
      )
      const errMsg = err.response?.data?.detail || 'Error updating candidate pipeline stage. Verify permissions or stage rules.'
      alert(`Move rejected: ${errMsg}`)
    }
  }

  const handleStageAction = async (appId: string, name: string, targetStageId: string) => {
    const app = applications.find((a) => a.id === appId)
    if (!app) return

    const originalStageId = app.current_stage_id

    // Optimistic UI Update
    setApplications((prev) =>
      prev.map((a) => (a.id === appId ? { ...a, current_stage_id: targetStageId, updated_at: new Date().toISOString() } : a))
    )

    try {
      await moveApplicationStage(appId, {
        target_stage_id: targetStageId,
        client_updated_at: app.updated_at
      })
      alert(`Candidate ${name} successfully transitioned stage.`)
    } catch (err: any) {
      // Revert card position on failure
      setApplications((prev) =>
        prev.map((a) => (a.id === appId ? { ...a, current_stage_id: originalStageId } : a))
      )
      const errMsg = err.response?.data?.detail || 'Error updating candidate stage.'
      alert(`Stage transition rejected: ${errMsg}`)
    }
  }

  return (
    <AppLayout>
      <div style={{ paddingBottom: 'var(--spacing-12)', height: '100%', display: 'flex', flexDirection: 'column' }}>
        
        {/* Header Title with Job Selector */}
        <header style={{ marginBottom: 'var(--spacing-24)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h1 className="font-signifier" style={{ fontSize: 'var(--text-heading-sm)', fontWeight: 500, color: 'var(--color-ink)', margin: 0 }}>
              Hiring Pipeline Board
            </h1>
            <p style={{ fontSize: 'var(--text-caption)', color: 'var(--color-ash)', marginTop: 'var(--spacing-8)', marginBottom: 0 }}>
              Expose applicant flow, drag and drop cards to trigger transitions, and manage custom workflows.
            </p>
          </div>

          {/* Job Dropdown Selector */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--color-ash)' }}>Select Job:</span>
            <select
              value={selectedJobId}
              onChange={(e) => setSelectedJobId(e.target.value)}
              style={{
                padding: '8px 16px',
                borderRadius: '8px',
                border: '1px solid var(--border)',
                background: 'var(--surface)',
                fontSize: '13px',
                fontWeight: 600,
                outline: 'none',
                cursor: 'pointer'
              }}
            >
              {jobs.map((j) => (
                <option key={j.id} value={j.id}>{j.title} ({j.department})</option>
              ))}
            </select>
          </div>
        </header>

        {error && (
          <div style={{ padding: '16px', background: '#fee2e2', color: '#b91c1c', borderRadius: '8px', marginBottom: '24px', fontSize: '13px', fontWeight: 500 }}>
            ⚠️ {error}
          </div>
        )}

        {/* Kanban Board Container */}
        <div
          style={{
            flex: 1,
            display: 'flex',
            gap: 'var(--spacing-16)',
            overflowX: 'auto',
            alignItems: 'stretch',
            minHeight: '620px',
            paddingBottom: 'var(--spacing-16)'
          }}
          aria-label="Hiring columns board"
        >
          {loading || stagesLoading ? (
            // Skeleton Loading State
            <div style={{ display: 'flex', gap: 'var(--spacing-16)', width: '100%' }}>
              {[1, 2, 3, 4].map((i) => (
                <div key={i} style={{ width: '280px', minWidth: '280px', background: 'var(--bg-subtle)', borderRadius: '12px', padding: '12px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
                  <div style={{ height: '20px', background: '#e5e7eb', borderRadius: '4px', width: '60%' }} />
                  <div style={{ height: '120px', background: '#f3f4f6', borderRadius: '8px', marginTop: '12px' }} />
                  <div style={{ height: '120px', background: '#f3f4f6', borderRadius: '8px', marginTop: '12px' }} />
                </div>
              ))}
            </div>
          ) : stages.length === 0 ? (
            <div style={{ padding: '48px', margin: '0 auto', color: 'var(--color-ash)' }}>No stages defined for this job.</div>
          ) : (
            stages.map((stage) => {
              const metrics = columnMetrics[stage.id] || { count: 0, avgScore: 0, avgDays: 0, hasBreach: false }
              const stageApps = applications.filter((app) => app.current_stage_id === stage.id)
              const isHovered = dragOverColumnId === stage.id

              return (
                <div
                  key={stage.id}
                  onDragOver={(e) => handleDragOver(e, stage.id)}
                  onDragLeave={handleDragLeave}
                  onDrop={(e) => handleDrop(e, stage.id)}
                  style={{
                    width: '280px',
                    minWidth: '280px',
                    background: isHovered ? 'var(--color-fog)' : 'transparent',
                    borderRadius: 'var(--radius-cards)',
                    border: isHovered ? '1.5px dashed var(--color-rust)' : '1px dashed var(--border)',
                    padding: 'var(--spacing-12)',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: 'var(--spacing-16)',
                    transition: 'background var(--duration-fast), border-color var(--duration-fast)',
                  }}
                >
                  {/* Column Header Metadata */}
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <h3 style={{ fontSize: '11px', fontWeight: 700, letterSpacing: '0.05em', textTransform: 'uppercase', margin: 0, color: 'var(--color-ash)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <span style={{ display: 'inline-block', width: '8px', height: '8px', borderRadius: '50%', background: stage.color || '#9ca3af' }} />
                        {stage.name}
                        {metrics.hasBreach && (
                          <span style={{ fontSize: '9px', padding: '1px 4px', background: '#fee2e2', color: '#ef4444', borderRadius: '4px', marginLeft: '4px', fontWeight: 600 }}>SLA 🔥</span>
                        )}
                      </h3>
                      <SteepBadge variant="neutral">
                        {metrics.count}
                      </SteepBadge>
                    </div>

                    {/* Aggregated Column Metrics */}
                    <div style={{ display: 'flex', gap: '8px', fontSize: '10px', color: 'var(--color-ash)', marginTop: '6px', fontWeight: 500 }}>
                      {metrics.count > 0 && (
                        <>
                          <span>Avg AI: <strong style={{ color: 'var(--color-ink)', fontWeight: 600 }}>{metrics.avgScore}%</strong></span>
                          <span>·</span>
                          <span>Avg Time: <strong style={{ color: 'var(--color-ink)', fontWeight: 600 }}>{metrics.avgDays}d</strong></span>
                        </>
                      )}
                    </div>
                  </div>

                  {/* Cards Container */}
                  <div
                    style={{
                      flex: 1,
                      display: 'flex',
                      flexDirection: 'column',
                      gap: 'var(--spacing-12)',
                      overflowY: 'auto'
                    }}
                    aria-label={`Candidates in ${stage.name}`}
                  >
                    {stageApps.map((app, index) => {
                      const score = app.match_score || 0
                      const diffTime = Math.abs(new Date(app.updated_at).getTime() - new Date(app.created_at).getTime())
                      const days = Math.ceil(diffTime / (1000 * 60 * 60 * 24))

                      // Check card level SLA breach
                      const isCardSlaBreached = stage.sla_enabled && stage.sla_hours && (days * 24 > stage.sla_hours)

                      return (
                        <div
                          key={app.id}
                          draggable
                          onDragStart={(e: any) => handleDragStart(e, app.id)}
                          style={{ cursor: 'grab' }}
                        >
                          <motion.div
                            layout
                            custom={index}
                            initial="hidden"
                            animate="visible"
                            variants={cardVariants}
                            transition={{ duration: 0.2, ease: 'easeOut' as any }}
                            style={{ height: '100%' }}
                          >
                            <SteepCard
                              padding="compact"
                              style={{
                                display: 'flex',
                                flexDirection: 'column',
                                gap: 'var(--spacing-12)',
                                position: 'relative',
                                border: isCardSlaBreached ? '1px solid #fee2e2' : undefined,
                                background: isCardSlaBreached ? '#fffbfb' : undefined
                              }}
                            >
                              {/* Card Header: Avatar & AI score */}
                              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                  <div style={{
                                    width: '24px',
                                    height: '24px',
                                    borderRadius: '50%',
                                    background: 'var(--surface-cool-tint)', 
                                    color: 'var(--color-ink)',
                                    display: 'grid',
                                    placeItems: 'center',
                                    fontWeight: 500,
                                    fontSize: '10px'
                                  }}>
                                    {app.candidate?.full_name ? app.candidate.full_name[0] : 'C'}
                                  </div>
                                  <strong style={{ fontSize: '13px', fontWeight: 500, color: 'var(--color-ink)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: '140px' }}>
                                    {app.candidate?.full_name}
                                  </strong>
                                </div>
                                
                                <MatchScoreBadge score={score > 0 ? score : null} size={28} strokeWidth={3} />
                              </div>

                              {/* Job connection & Days Badge */}
                              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', fontSize: '11px' }}>
                                <span style={{ color: 'var(--color-ash)', fontWeight: 400, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '150px' }}>
                                  {app.job?.title || 'General Opening'}
                                </span>
                                <span style={{ color: isCardSlaBreached ? '#ef4444' : 'var(--color-ash)', fontWeight: isCardSlaBreached ? 600 : 400 }}>
                                  {days}d here {isCardSlaBreached && '⚠️'}
                                </span>
                              </div>

                              {/* Card hover operational triggers */}
                              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px', borderTop: '1px solid var(--border)', paddingTop: 'var(--spacing-8)', marginTop: '4px' }}>
                                <SteepButton
                                  variant="secondary"
                                  size="sm"
                                  style={{ padding: '3px 6px', fontSize: '9.5px' }}
                                  onClick={() => {
                                    setSelectedApp(app)
                                    setDrawerTab('overview')
                                  }}
                                >
                                  View
                                </SteepButton>
                                <SteepButton
                                  variant="secondary"
                                  size="sm"
                                  style={{ padding: '3px 6px', fontSize: '9.5px' }}
                                  onClick={() => {
                                    setSelectedApp(app)
                                    setDrawerTab('interviews')
                                  }}
                                >
                                  Schedule
                                </SteepButton>
                                
                                {/* Quick transition shortcuts to Offer and Reject */}
                                {stages.map((stg) => {
                                  if (stg.base_category === 'offered' && stg.id !== stage.id) {
                                    return (
                                      <SteepButton
                                        key={stg.id}
                                        variant="secondary"
                                        size="sm"
                                        style={{ padding: '3px 6px', fontSize: '9.5px' }}
                                        onClick={() => handleStageAction(app.id, app.candidate?.full_name || 'Candidate', stg.id)}
                                      >
                                        Offer
                                      </SteepButton>
                                    )
                                  }
                                  if (stg.base_category === 'rejected' && stg.id !== stage.id) {
                                    return (
                                      <SteepButton
                                        key={stg.id}
                                        variant="secondary"
                                        size="sm"
                                        style={{ padding: '3px 6px', fontSize: '9.5px', color: 'var(--color-rust)' }}
                                        onClick={() => handleStageAction(app.id, app.candidate?.full_name || 'Candidate', stg.id)}
                                      >
                                        Reject
                                      </SteepButton>
                                    )
                                  }
                                  return null
                                })}
                                
                                <SteepButton
                                  variant="secondary"
                                  size="sm"
                                  style={{ padding: '3px 6px', fontSize: '9.5px' }}
                                  onClick={() => {
                                    setSelectedApp(app)
                                    setDrawerTab('timeline')
                                  }}
                                >
                                  Note
                                </SteepButton>
                              </div>
                            </SteepCard>
                          </motion.div>
                        </div>
                      )
                    })}
                    
                    {stageApps.length === 0 && (
                      <div style={{ textAlign: 'center', padding: 'var(--spacing-16) 0', color: 'var(--color-ash)', fontSize: '12px', border: '1px dashed var(--border)', borderRadius: 'var(--radius-cards)' }}>
                        Empty Stage
                      </div>
                    )}
                  </div>

                </div>
              )
            })
          )}
        </div>

        {/* Flagship Candidate detail drawer */}
        {selectedApp && (
          <CandidateDrawer
            application={selectedApp}
            tab={drawerTab}
            onTabChange={setDrawerTab}
            onClose={() => setSelectedApp(null)}
            onStageChanged={() => loadJobData(selectedJobId)}
          />
        )}

      </div>
    </AppLayout>
  )
}
