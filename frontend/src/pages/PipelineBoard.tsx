import { useState, useEffect, useMemo } from 'react'
import { motion, type Variants } from 'framer-motion'
import AppLayout from '../components/AppLayout'
import CandidateDrawer from '../components/CandidateDrawer'
import { fetchApplications, updateApplicationStatus, type Application } from '../api'
import { scoreClass } from '../utils/score'
import SteepCard from '../components/design-system/SteepCard'
import SteepButton from '../components/design-system/SteepButton'
import SteepBadge from '../components/design-system/SteepBadge'

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

const COLUMNS = [
  { id: 'SCREENING', title: 'Applied / Screening' },
  { id: 'INTERVIEW', title: 'Interview Panel' },
  { id: 'COMMITTEE', title: 'Committee Review' },
  { id: 'OFFER', title: 'Offer Contract' },
  { id: 'HIRED', title: 'Hired & Sync' },
]

export default function PipelineBoard() {
  const [applications, setApplications] = useState<Application[]>([])

  // Drawer candidate state
  const [selectedApp, setSelectedApp] = useState<Application | null>(null)
  const [drawerTab, setDrawerTab] = useState<'overview' | 'screening' | 'interviews' | 'offers' | 'timeline'>('overview')

  // Drag over column state highlighting
  const [dragOverColumnId, setDragOverColumnId] = useState<string | null>(null)

  const loadData = async () => {
    try {
      const appList = await fetchApplications()
      setApplications(appList)
    } catch (err) {
      console.error('Error fetching pipeline applications:', err)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  // --- Dynamic Mock Metadata calculations per column ---
  const columnMetrics = useMemo(() => {
    const metrics: Record<string, { count: number; avgScore: number; avgDays: number }> = {}

    COLUMNS.forEach((col) => {
      const colApps = applications.filter(
        (app) => {
          const status = app.status.toUpperCase()
          // map basic 'applied' or 'screening' to SCREENING column
          if (col.id === 'SCREENING') return status === 'SCREENING' || status === 'APPLIED' || status === 'REJECTED'
          return status === col.id
        }
      )

      const count = colApps.length
      
      // Calculate deterministic average scores & days in stage based on hashes
      let totalScore = 0
      let totalDays = 0

      colApps.forEach((app) => {
        const hashNum = Math.abs(app.id.charCodeAt(0) + app.id.charCodeAt(5))
        totalScore += (hashNum % 40) + 60
        totalDays += (hashNum % 12) + 1
      })

      const avgScore = count > 0 ? Math.round(totalScore / count) : 0
      const avgDays = count > 0 ? Math.round(totalDays / count) : 0

      metrics[col.id] = { count, avgScore, avgDays }
    })

    return metrics
  }, [applications])

  // --- HTML5 Drag and Drop handlers (Type-Safe and Highly Compatible) ---
  const handleDragStart = (e: React.DragEvent, appId: string) => {
    e.dataTransfer.setData('text/plain', appId)
    e.dataTransfer.effectAllowed = 'move'
  }

  const handleDragOver = (e: React.DragEvent, columnId: string) => {
    e.preventDefault()
    setDragOverColumnId(columnId)
  }

  const handleDragLeave = () => {
    setDragOverColumnId(null)
  }

  const handleDrop = async (e: React.DragEvent, targetColumnId: string) => {
    e.preventDefault()
    setDragOverColumnId(null)
    const appId = e.dataTransfer.getData('text/plain')
    if (!appId) return

    // Find the application
    const app = applications.find((a) => a.id === appId)
    if (!app) return

    // Don't transition if same column
    const currentColumn = app.status.toUpperCase()
    const targetStatus = targetColumnId.toLowerCase()
    
    if (currentColumn === targetColumnId || (targetColumnId === 'SCREENING' && currentColumn === 'APPLIED')) {
      return
    }

    try {
      // Optimistic update
      setApplications((prev) =>
        prev.map((a) => (a.id === appId ? { ...a, status: targetStatus } : a))
      )

      await updateApplicationStatus(appId, targetStatus)
      alert(`Successfully advanced ${app.candidate?.full_name || 'candidate'} to stage: ${targetColumnId}`)
      loadData()
    } catch (err) {
      alert('Error updating candidate pipeline stage. Verify RLS bounds.')
      loadData()
    }
  }

  return (
    <AppLayout>
      <div style={{ paddingBottom: 'var(--spacing-12)', height: '100%', display: 'flex', flexDirection: 'column' }}>
        
        {/* Header Title */}
        <header style={{ marginBottom: 'var(--spacing-24)' }}>
          <h1 className="font-signifier" style={{ fontSize: 'var(--text-heading-sm)', fontWeight: 500, color: 'var(--color-ink)', margin: 0 }}>
            Hiring Pipeline Board
          </h1>
          <p style={{ fontSize: 'var(--text-caption)', color: 'var(--color-ash)', marginTop: 'var(--spacing-8)', marginBottom: 0 }}>
            Expose applicant flow, drag and drop cards to trigger transitions, and manage panelists scorecards live.
          </p>
        </header>

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
          {COLUMNS.map((col) => {
            const metrics = columnMetrics[col.id] || { count: 0, avgScore: 0, avgDays: 0 }
            const colApps = applications.filter((app) => {
              const status = app.status.toUpperCase()
              if (col.id === 'SCREENING') return status === 'SCREENING' || status === 'APPLIED' || status === 'REJECTED'
              return status === col.id
            })

            const isHovered = dragOverColumnId === col.id

            return (
              <div
                key={col.id}
                onDragOver={(e) => handleDragOver(e, col.id)}
                onDragLeave={handleDragLeave}
                onDrop={(e) => handleDrop(e, col.id)}
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
                    <h3 style={{ fontSize: '10px', fontWeight: 600, letterSpacing: '0.05em', textTransform: 'uppercase', margin: 0, color: 'var(--color-ash)' }}>
                      {col.title}
                    </h3>
                    <SteepBadge variant="neutral">
                      {metrics.count}
                    </SteepBadge>
                  </div>

                  {/* Aggregated Column Metrics */}
                  <div style={{ display: 'flex', gap: '8px', fontSize: '10px', color: 'var(--color-ash)', marginTop: '6px', fontWeight: 500 }}>
                    <span>Avg AI: <strong style={{ color: 'var(--color-ink)', fontWeight: 600 }}>{metrics.avgScore}%</strong></span>
                    <span>·</span>
                    <span>Avg Time: <strong style={{ color: 'var(--color-ink)', fontWeight: 600 }}>{metrics.avgDays}d</strong></span>
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
                  aria-label={`Candidates in ${col.title}`}
                >
                  {colApps.map((app, index) => {
                    const hashNum = Math.abs(app.id.charCodeAt(0) + app.id.charCodeAt(5))
                    const score = (hashNum % 40) + 60
                    const days = (hashNum % 12) + 1

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
                              position: 'relative'
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
                                <strong style={{ fontSize: '13.5px', fontWeight: 500, color: 'var(--color-ink)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: '140px' }}>
                                  {app.candidate?.full_name}
                                </strong>
                              </div>
                              
                              <span className={`score-ring ${scoreClass(score)}`} style={{ width: '22px', height: '22px', fontSize: '9px' }}>
                                {score}
                              </span>
                            </div>

                            {/* Job connection & Days Badge */}
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', fontSize: '11px' }}>
                              <span style={{ color: 'var(--color-ash)', fontWeight: 400, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '150px' }}>
                                {app.job?.title || 'General Opening'}
                              </span>
                              <span style={{ color: 'var(--color-ash)', fontWeight: 400 }}>
                                {days}d here
                              </span>
                            </div>

                            {/* Card hover operational triggers */}
                            <div style={{ display: 'flex', gap: '6px', borderTop: '1px solid var(--border)', paddingTop: 'var(--spacing-8)' }}>
                              <SteepButton
                                variant="secondary"
                                size="sm"
                                style={{ flex: 1, padding: '4px 6px', fontSize: '10px' }}
                                onClick={() => {
                                  setSelectedApp(app)
                                  setDrawerTab('overview')
                                }}
                              >
                                Open
                              </SteepButton>
                              {app.status.toLowerCase() !== 'hired' && (
                                <SteepButton
                                  variant="secondary"
                                  size="sm"
                                  style={{ flex: 1, padding: '4px 6px', fontSize: '10px' }}
                                  onClick={() => {
                                    setSelectedApp(app)
                                    setDrawerTab('interviews')
                                  }}
                                >
                                  Schedule
                                </SteepButton>
                              )}
                            </div>
                          </SteepCard>
                        </motion.div>
                      </div>
                    )
                  })}
                  
                  {colApps.length === 0 && (
                    <div style={{ textAlign: 'center', padding: 'var(--spacing-16) 0', color: 'var(--color-ash)', fontSize: '12px', border: '1px dashed var(--border)', borderRadius: 'var(--radius-cards)' }}>
                      Drag cards here
                    </div>
                  )}
                </div>

              </div>
            )
          })}
        </div>

        {/* Flagship Candidate detail drawer */}
        {selectedApp && (
          <CandidateDrawer
            application={selectedApp}
            tab={drawerTab}
            onTabChange={setDrawerTab}
            onClose={() => setSelectedApp(null)}
            onStageChanged={loadData}
          />
        )}

      </div>
    </AppLayout>
  )
}

