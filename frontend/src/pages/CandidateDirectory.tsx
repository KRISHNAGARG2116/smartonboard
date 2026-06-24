import { useState, useEffect, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import AppLayout from '../components/AppLayout'
import DataTable from '../components/DataTable'
import type { DataTableColumn, DataTableFilter, DataTableBulkAction } from '../components/DataTable'
import CandidateDrawer from '../components/CandidateDrawer'
import { fetchApplications, fetchJobs, updateApplicationStatus, type Application, type Job } from '../api'
import { scoreClass } from '../utils/score'
import EmptyState from '../components/EmptyState'

export default function CandidateDirectory() {
  const navigate = useNavigate()
  const [applications, setApplications] = useState<Application[]>([])
  const [jobs, setJobs] = useState<Job[]>([])
  const [loading, setLoading] = useState(true)
  // Filter states
  const [stageFilter, setStageFilter] = useState('')
  const [jobFilter, setJobFilter] = useState('')

  // Drawer selected candidate
  const [selectedApp, setSelectedApp] = useState<Application | null>(null)
  const [drawerTab, setDrawerTab] = useState<'overview' | 'screening' | 'interviews' | 'offers' | 'timeline'>('overview')

  const loadData = async () => {
    setLoading(true)
    try {
      const [appList, jobList] = await Promise.all([
        fetchApplications(),
        fetchJobs(),
      ])
      setApplications(appList)
      setJobs(jobList)
    } catch (err) {
      console.error('Error loading candidate records:', err)
    } finally {
      setLoading(false)
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
              background: 'var(--color-dark-cork)', color: 'var(--color-pure-white)',
              display: 'grid',
              placeItems: 'center',
              fontWeight: 500,
              fontSize: '12px'
            }}>
              {app.candidate?.full_name ? app.candidate.full_name[0] : 'C'}
            </div>
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <span style={{ fontWeight: 500, color: 'var(--text)' }}>
                {app.candidate?.full_name || 'Unknown Candidate'}
              </span>
              <span style={{ fontSize: '11px', color: 'var(--color-grey-brown)' }}>
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
          <span className={`badge ${stageBadgeClass(app.status)}`} style={{ fontSize: '9px', fontWeight: 500 }}>
            {app.status}
          </span>
        )
      },
      {
        key: 'match_score',
        header: 'AI Match Score',
        sortable: true,
        render: (app) => {
          const score = app.match_score
          if (score === undefined || score === null) {
            return (
              <span className="badge badge--neutral" style={{ fontSize: '10px', padding: '4px 8px' }}>
                N/A
              </span>
            )
          }
          const roundedScore = Math.round(score)
          return (
            <span className={`score-ring ${scoreClass(roundedScore)}`} style={{ width: '28px', height: '28px', fontSize: '11px' }}>
              {roundedScore}
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
            <div style={{ fontWeight: 500 }}>{app.job?.title || 'General Opening'}</div>
            <div style={{ fontSize: '11px', color: 'var(--color-grey-brown)', marginTop: '2px' }}>{app.job?.department || 'Operations'}</div>
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
            <div style={{ width: '20px', height: '20px', borderRadius: '50%', background: 'var(--color-dark-cork)', color: 'var(--color-pure-white)', display: 'grid', placeItems: 'center', fontWeight: 500, fontSize: '8px' }}>R</div>
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
            style={{ padding: '4px 10px' }}
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
          <h1 style={{ fontSize: '29px', fontWeight: 500, letterSpacing: '-0.02em', marginBottom: '4px', lineHeight: 1.09, color: 'var(--text)' }}>
            Candidates Workspace Directory
          </h1>
          <p className="text-secondary" style={{ fontSize: '14px', lineHeight: 1.33 }}>
            Expose and manage applicant portfolios, match metrics, and scheduled panels using our RLS-bounded search engine.
          </p>
        </header>

        {/* Generic DataTable Component */}
        {!loading && applications.length === 0 ? (
          <EmptyState
            type="applications"
            title="No Candidates Found"
            description="There are currently no active applications or screened candidate records tracked in your workspace."
            actionLabel="Return to Command Center"
            onAction={() => navigate('/recruiter/dashboard')}
          />
        ) : (
          <DataTable
            data={applications}
            columns={columns}
            getRowId={(app) => app.id}
            searchPlaceholder="Search candidates by name, email, or job role..."
            searchKeys={['candidate.full_name', 'candidate.email', 'job.title']}
            filters={dataFilters}
            bulkActions={bulkActions}
            loading={loading}
          />
        )}

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
