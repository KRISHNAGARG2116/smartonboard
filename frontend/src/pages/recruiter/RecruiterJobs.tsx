import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import AppLayout from '../../components/AppLayout'
import { 
  fetchJobs, 
  updateJob, 
  fetchApplications, 
  type Job, 
  type Application 
} from '../../api'
import SteepCard from '../../components/design-system/SteepCard'
import SteepButton from '../../components/design-system/SteepButton'
import SteepBadge from '../../components/design-system/SteepBadge'

export default function RecruiterJobs() {
  const navigate = useNavigate()
  const [jobs, setJobs] = useState<Job[]>([])
  const [applications, setApplications] = useState<Application[]>([])
  const [loading, setLoading] = useState(true)

  // Fetch job listings
  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const [jobList, appList] = await Promise.all([
        fetchJobs(),
        fetchApplications()
      ])
      setJobs(jobList)
      setApplications(appList)
    } catch (err) {
      console.error('Error fetching jobs or applications:', err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadData()
  }, [loadData])

  // Toggle status from index list (open / closed)
  const handleToggleStatus = async (job: Job) => {
    const newStatus = job.status === 'open' ? 'closed' : 'open'
    try {
      // Optimistic update of title/fields preserves existing concurrency model
      await updateJob(job.id, { 
        status: newStatus,
        client_updated_at: job.updated_at
      })
      alert(`Job status updated to ${newStatus}`)
      loadData()
    } catch (err: any) {
      if (err.response?.status === 409) {
        alert('This job post has been updated elsewhere. Please refresh the page and try again.')
      } else {
        alert('Error updating job status.')
      }
    }
  }

  return (
    <AppLayout>
      <div className="container" style={{ padding: 'var(--spacing-32) 0 var(--spacing-48)' }}>
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
              Workspace Openings
            </span>
            <h1 className="font-signifier" style={{ fontSize: 'var(--text-heading-sm)', fontWeight: 500, color: 'var(--color-ink)', margin: '4px 0 0', lineHeight: 1.09 }}>
              Job Postings
            </h1>
          </div>
          <SteepButton 
            onClick={() => navigate('/recruiter/jobs/new')}
            variant="primary"
          >
            Create Job
          </SteepButton>
        </div>

        {loading ? (
          <div style={{ padding: 'var(--spacing-48) 0', textAlign: 'center', color: 'var(--color-ash)' }}>
            Loading active job postings...
          </div>
        ) : jobs.length === 0 ? (
          <SteepCard style={{ textAlign: 'center', padding: 'var(--spacing-48)' }}>
            No active job postings. Click "Create Job" to post your first opening.
          </SteepCard>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-16)' }}>
            {jobs.map((job) => {
              const count = applications.filter((app) => app.job_id === job.id).length
              return (
                <GridSteepCard 
                  key={job.id}
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    padding: 'var(--spacing-16) var(--spacing-24)'
                  }}
                >
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                      <h3 style={{ fontSize: 'var(--text-body-lg)', fontWeight: 500, color: 'var(--color-ink)', margin: 0 }}>
                        {job.title}
                      </h3>
                      <SteepBadge variant={job.status === 'open' ? 'success' : 'neutral'}>
                        {job.status}
                      </SteepBadge>
                    </div>
                    <div style={{ display: 'flex', gap: 12, marginTop: 4, fontSize: 'var(--text-caption)', color: 'var(--color-ash)' }}>
                      <span>{job.department}</span>
                      <span>&bull;</span>
                      {job.settings?.workplace_type && (
                        <span>{job.settings.workplace_type}</span>
                      )}
                    </div>
                  </div>
                  
                  <div style={{ display: 'flex', alignItems: 'center', gap: '24px' }}>
                    <div style={{ fontSize: 'var(--text-body)', color: 'var(--color-ash)', textAlign: 'right' }}>
                      Active Applicants: <strong style={{ color: 'var(--color-ink)' }}>{count}</strong>
                    </div>
                    <div style={{ display: 'flex', gap: '8px' }}>
                      <SteepButton
                        variant="secondary"
                        size="sm"
                        onClick={() => navigate(`/recruiter/jobs/${job.id}/edit`)}
                      >
                        Edit
                      </SteepButton>
                      <SteepButton
                        variant="secondary"
                        size="sm"
                        onClick={() => handleToggleStatus(job)}
                      >
                        {job.status === 'open' ? 'Close' : 'Re-open'}
                      </SteepButton>
                    </div>
                  </div>
                </GridSteepCard>
              )
            })}
          </div>
        )}
      </div>
    </AppLayout>
  )
}

// Simple styling helper to wrap card content
function GridSteepCard({ children, style, ...props }: any) {
  return (
    <SteepCard style={style} {...props}>
      {children}
    </SteepCard>
  )
}
