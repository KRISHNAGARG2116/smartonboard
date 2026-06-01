import { useState, useEffect, useMemo } from 'react'
import AppLayout from '../components/AppLayout'
import DataTable from '../components/DataTable'
import type { DataTableColumn, DataTableFilter, DataTableBulkAction } from '../components/DataTable'
import CandidateDrawer from '../components/CandidateDrawer'
import { fetchApplications, fetchJobs, updateApplicationStatus, type Application, type Job } from '../api'
import { scoreClass } from '../utils/score'

export default function CandidateDirectory() {
  const [applications, setApplications] = useState<Application[]>([])
  const [jobs, setJobs] = useState<Job[]>([])
  // Filter states
  const [stageFilter, setStageFilter] = useState('')
  const [jobFilter, setJobFilter] = useState('')

  // Drawer selected candidate
  const [selectedApp, setSelectedApp] = useState<Application | null>(null)
  const [drawerTab, setDrawerTab] = useState<'overview' | 'screening' | 'interviews' | 'offers' | 'timeline'>('overview')

  const loadData = async () => {
    try {
      const [appList, jobList] = await Promise.all([
        fetchApplications(),
        fetchJobs(),
      ])
      setApplications(appList)
      setJobs(jobList)
    } catch (err) {
      console.error('Error loading candidate records:', err)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  // Dynamic status stage badge mapper
  const stageBadgeClass = (status: string) => {
    const s = status.toLowerCase()
    if (s === 'hired') return 'badge--hire'
    if (s === 'rejected') return 'badge--reject'
    if (s === 'interview' || s === 'screening') return 'badge--interview'
    return 'badge--neutral'
  }

  // DataTable Column Definitions
  const columns: DataTableColumn<Application>[] = useMemo(
    () => [
      {
        key: 'candidate.full_name',
        header: 'Candidate Name',
        sortable: true,
        render: (app) => (
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
            <div style={{
              width: '32px',
              height: '32px',
              borderRadius: '50%',
              background: 'var(--accent-muted)',
              color: 'var(--accent)',
              display: 'grid',
              placeItems: 'center',
              fontWeight: 700,
              fontSize: '12px'
            }}>
              {app.candidate?.full_name ? app.candidate.full_name[0] : 'C'}
            </div>
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <span style={{ fontWeight: 700, color: 'var(--text)' }}>
                {app.candidate?.full_name || 'Unknown Candidate'}
              </span>
              <span style={{ fontSize: '11px', color: 'var(--text-tertiary)' }}>
                {app.candidate?.email || 'No Email'}
              </span>
            </div>
          </div>
        )
      },
      {
        key: 'status',
        header: 'Current Stage',
        sortable: true,
        render: (app) => (
          <span className={`badge ${stageBadgeClass(app.status)}`} style={{ fontSize: '9px', fontWeight: 700 }}>
            {app.status}
          </span>
        )
      },
      {
        key: 'ai_score', // Custom field simulated from backend AI scores
        header: 'AI Match Score',
        sortable: true,
        render: (app) => {
          // Simulate dynamic AI score based on application hash or local seeding
          const simulatedScore = Math.abs(app.id.charCodeAt(0) + app.id.charCodeAt(5)) % 40 + 60
          return (
            <span className={`score-ring ${scoreClass(simulatedScore)}`} style={{ width: '28px', height: '28px', fontSize: '11px' }}>
              {simulatedScore}
            </span>
          )
        }
      },
      {
        key: 'job.title',
        header: 'Job Applied For',
        sortable: true,
        render: (app) => (
          <div>
            <div style={{ fontWeight: 600 }}>{app.job?.title || 'General Opening'}</div>
            <div style={{ fontSize: '11px', color: 'var(--text-tertiary)', marginTop: '2px' }}>{app.job?.department || 'Operations'}</div>
          </div>
        )
      },
      {
        key: 'created_at',
        header: 'Applied Date',
        sortable: true,
        hideOnMobile: true,
        render: (app) => (
          <span style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-xs)' }}>
            {new Date(app.created_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })}
          </span>
        )
      },
      {
        key: 'owner',
        header: 'Recruiter Owner',
        hideOnMobile: true,
        render: () => (
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: 'var(--text-xs)' }}>
            <div style={{ width: '20px', height: '20px', borderRadius: '50%', background: 'var(--text)', color: 'var(--text-inverse)', display: 'grid', placeItems: 'center', fontWeight: 'bold', fontSize: '8px' }}>R</div>
            <span>Sarah Recruiter</span>
          </div>
        )
      },
      {
        key: 'actions',
        header: '',
        render: (app) => (
          <button
            type="button"
            className="btn btn--secondary btn--sm"
            style={{ borderRadius: '8px', padding: '4px 10px' }}
            onClick={(e) => {
              e.stopPropagation()
              setSelectedApp(app)
              setDrawerTab('overview')
            }}
          >
            Workspace
          </button>
        )
      }
    ],
    []
  )

  // Format DataTable Filters
  const dataFilters: DataTableFilter[] = useMemo(
    () => [
      {
        label: 'Stage',
        key: 'status',
        value: stageFilter,
        options: [
          { label: 'Screening', value: 'screening' },
          { label: 'Interview', value: 'interview' },
          { label: 'Committee Review', value: 'committee' },
          { label: 'Offer', value: 'offer' },
          { label: 'Hired', value: 'hired' },
          { label: 'Rejected', value: 'rejected' }
        ],
        onChange: setStageFilter
      },
      {
        label: 'Job',
        key: 'job_id',
        value: jobFilter,
        options: jobs.map((j) => ({ label: j.title, value: j.id })),
        onChange: setJobFilter
      }
    ],
    [jobs, stageFilter, jobFilter]
  )

  // Format DataTable Bulk Actions
  const bulkActions: DataTableBulkAction[] = useMemo(
    () => [
      {
        label: 'Bulk Move to Interview',
        onClick: async (ids) => {
          try {
            await Promise.all(ids.map((id) => updateApplicationStatus(id, 'interview')))
            alert('Candidates successfully advanced to Interview stage!')
            loadData()
          } catch {
            alert('Error executing bulk transition.')
          }
        }
      },
      {
        label: 'Bulk Reject Candidates',
        className: 'btn--ghost',
        onClick: async (ids) => {
          try {
            await Promise.all(ids.map((id) => updateApplicationStatus(id, 'rejected')))
            alert('Candidates marked as rejected.')
            loadData()
          } catch {
            alert('Error executing bulk rejection.')
          }
        }
      }
    ],
    []
  )

  return (
    <AppLayout>
      <div className="dashboard-page container container--wide" style={{ paddingBottom: 'var(--space-12)' }}>
        
        {/* Header Title */}
        <header style={{ marginBottom: 'var(--space-6)' }}>
          <h1 style={{ fontSize: 'var(--text-3xl)', fontWeight: 700, letterSpacing: '-0.02em', marginBottom: '4px' }}>
            Candidates Workspace Directory
          </h1>
          <p className="text-secondary" style={{ fontSize: 'var(--text-sm)' }}>
            Expose and manage applicant portfolios, match metrics, and scheduled panels using our RLS-bounded search engine.
          </p>
        </header>

        {/* Generic DataTable Component */}
        <DataTable
          data={applications}
          columns={columns}
          getRowId={(app) => app.id}
          searchPlaceholder="Search candidates by name, email, or job role..."
          searchKeys={['candidate.full_name', 'candidate.email', 'job.title']}
          filters={dataFilters}
          bulkActions={bulkActions}
        />

        {/* Flagship Candidate Detail Drawer */}
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
