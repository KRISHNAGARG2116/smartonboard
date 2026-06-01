import { useState, useEffect, useMemo } from 'react'
import AppLayout from '../components/AppLayout'
import CandidateDrawer from '../components/CandidateDrawer'
import { fetchApplications, updateApplicationStatus, type Application } from '../api'
import { scoreClass } from '../utils/score'

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
    } catch {
      alert('Error updating candidate pipeline stage. Verify RLS bounds.')
      loadData()
    }
  }

  return (
    <AppLayout>
      <div className="dashboard-page container container--wide" style={{ paddingBottom: 'var(--space-12)', height: '100%', display: 'flex', flexDirection: 'column' }}>
        
        {/* Header Title */}
        <header style={{ marginBottom: 'var(--space-6)' }}>
          <h1 style={{ fontSize: 'var(--text-3xl)', fontWeight: 700, letterSpacing: '-0.02em', marginBottom: '4px' }}>
            Hiring Pipeline Board
          </h1>
          <p className="text-secondary" style={{ fontSize: 'var(--text-sm)' }}>
            Expose applicant flow, drag and drop cards to trigger transitions, and manage panelists scorecards live.
          </p>
        </header>

        {/* Kanban Board Container */}
        <div
          style={{
            flex: 1,
            display: 'flex',
            gap: 'var(--space-4)',
            overflowX: 'auto',
            alignItems: 'stretch',
            minHeight: '620px',
            paddingBottom: 'var(--space-4)'
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
                  background: isHovered ? 'var(--accent-subtle)' : 'var(--bg-subtle)',
                  borderRadius: '20px',
                  border: isHovered ? '1.5px dashed var(--accent)' : '1px solid var(--border)',
                  padding: 'var(--space-4)',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 'var(--space-4)',
                  transition: 'background var(--duration-fast), border-color var(--duration-fast)',
                }}
              >
                {/* Column Header Metadata */}
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                    <h3 style={{ fontSize: 'var(--text-sm)', fontWeight: 700, margin: 0, color: 'var(--text)' }}>
                      {col.title}
                    </h3>
                    <span
                      style={{
                        fontSize: '10.5px',
                        fontWeight: 700,
                        padding: '2px 8px',
                        borderRadius: '6px',
                        background: 'var(--border)',
                        color: 'var(--text-secondary)'
                      }}
                    >
                      {metrics.count}
                    </span>
                  </div>

                  {/* Aggregated Column Metrics */}
                  <div style={{ display: 'flex', gap: '8px', fontSize: '10px', color: 'var(--text-tertiary)', marginTop: '6px', fontWeight: 600 }}>
                    <span>Avg AI: <strong style={{ color: 'var(--text-secondary)' }}>{metrics.avgScore}%</strong></span>
                    <span>·</span>
                    <span>Avg Time: <strong style={{ color: 'var(--text-secondary)' }}>{metrics.avgDays}d</strong></span>
                  </div>
                </div>

                {/* Cards Container */}
                <div
                  style={{
                    flex: 1,
                    display: 'flex',
                    flexDirection: 'column',
                    gap: 'var(--space-3)',
                    overflowY: 'auto'
                  }}
                  aria-label={`Candidates in ${col.title}`}
                >
                  {colApps.map((app) => {
                    const hashNum = Math.abs(app.id.charCodeAt(0) + app.id.charCodeAt(5))
                    const score = (hashNum % 40) + 60
                    const days = (hashNum % 12) + 1

                    return (
                      <article
                        key={app.id}
                        draggable
                        onDragStart={(e) => handleDragStart(e, app.id)}
                        style={{
                          padding: 'var(--space-4)',
                          background: 'var(--surface)',
                          border: '1px solid var(--border)',
                          borderRadius: '16px',
                          boxShadow: 'var(--shadow-sm)',
                          cursor: 'grab',
                          display: 'flex',
                          flexDirection: 'column',
                          gap: 'var(--space-2)',
                          transition: 'transform var(--duration-fast), box-shadow var(--duration-fast)',
                          position: 'relative'
                        }}
                        onMouseEnter={(e) => {
                          e.currentTarget.style.transform = 'translateY(-2px)'
                          e.currentTarget.style.boxShadow = 'var(--shadow-md)'
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.transform = 'none'
                          e.currentTarget.style.boxShadow = 'var(--shadow-sm)'
                        }}
                      >
                        {/* Card Header: Avatar & AI score */}
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <div style={{
                              width: '24px',
                              height: '24px',
                              borderRadius: '50%',
                              background: 'var(--accent-muted)',
                              color: 'var(--accent)',
                              display: 'grid',
                              placeItems: 'center',
                              fontWeight: 700,
                              fontSize: '10px'
                            }}>
                              {app.candidate?.full_name ? app.candidate.full_name[0] : 'C'}
                            </div>
                            <strong style={{ fontSize: 'var(--text-sm)', color: 'var(--text)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: '140px' }}>
                              {app.candidate?.full_name}
                            </strong>
                          </div>
                          
                          <span className={`score-ring ${scoreClass(score)}`} style={{ width: '22px', height: '22px', fontSize: '9px' }}>
                            {score}
                          </span>
                        </div>

                        {/* Job connection & Days Badge */}
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', fontSize: '11px', marginTop: '4px' }}>
                          <span style={{ color: 'var(--text-secondary)', fontWeight: 550, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '150px' }}>
                            {app.job?.title || 'General Opening'}
                          </span>
                          <span style={{ color: 'var(--text-tertiary)', fontWeight: 600 }}>
                            {days}d here
                          </span>
                        </div>

                        {/* Card hover operational triggers */}
                        <div style={{ display: 'flex', gap: '6px', marginTop: 'var(--space-2)', borderTop: '1px solid var(--border)', paddingTop: 'var(--space-2)' }}>
                          <button
                            type="button"
                            className="btn btn--secondary btn--sm btn--block"
                            style={{ borderRadius: '8px', padding: '4px 6px', fontSize: '10px', flex: 1 }}
                            onClick={() => {
                              setSelectedApp(app)
                              setDrawerTab('overview')
                            }}
                          >
                            Open
                          </button>
                          {app.status.toLowerCase() !== 'hired' && (
                            <button
                              type="button"
                              className="btn btn--secondary btn--sm btn--block"
                              style={{ borderRadius: '8px', padding: '4px 6px', fontSize: '10px', flex: 1 }}
                              onClick={() => {
                                setSelectedApp(app)
                                setDrawerTab('interviews')
                              }}
                            >
                              Schedule
                            </button>
                          )}
                        </div>
                      </article>
                    )
                  })}
                  
                  {colApps.length === 0 && (
                    <div style={{ textAlign: 'center', padding: 'var(--space-8) 0', color: 'var(--text-tertiary)', fontSize: 'var(--text-xs)', border: '1.5px dashed var(--border)', borderRadius: '12px' }}>
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
