import { useState, useEffect, useCallback } from 'react'
import AppLayout from '../../components/AppLayout'
import { fetchJobs, createJob, updateJob, fetchApplications, type Job, type Application } from '../../api'
import SteepCard from '../../components/design-system/SteepCard'
import SteepButton from '../../components/design-system/SteepButton'
import SteepInput from '../../components/design-system/SteepInput'
import SteepBadge from '../../components/design-system/SteepBadge'

export default function RecruiterJobs() {
  const [jobs, setJobs] = useState<Job[]>([])
  const [applications, setApplications] = useState<Application[]>([])
  const [loading, setLoading] = useState(true)
  
  // Modals state
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [isEditModalOpen, setIsEditModalOpen] = useState(false)
  const [editingJob, setEditingJob] = useState<Job | null>(null)

  // Create Form State
  const [title, setTitle] = useState('')
  const [dept, setDept] = useState('Engineering')
  const [desc, setDesc] = useState('')
  const [startDate, setStartDate] = useState('')
  const [submitting, setSubmitting] = useState(false)

  // Edit Form State
  const [editTitle, setEditTitle] = useState('')
  const [editDept, setEditDept] = useState('Engineering')
  const [editDesc, setEditDesc] = useState('')
  const [editStartDate, setEditStartDate] = useState('')
  const [editingSubmitting, setEditingSubmitting] = useState(false)

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
      console.error('Error fetching jobs and applications:', err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadData()
  }, [loadData])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSubmitting(true)
    try {
      await createJob({
        title,
        department: dept,
        description: desc,
        status: 'open',
        start_date: startDate || null
      })
      setIsModalOpen(false)
      setTitle('')
      setDesc('')
      setStartDate('')
      loadData()
    } catch (err) {
      alert('Error creating Job Posting.')
    } finally {
      setSubmitting(false)
    }
  }

  const handleEditSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!editingJob) return
    setEditingSubmitting(true)
    try {
      await updateJob(editingJob.id, {
        title: editTitle,
        department: editDept,
        description: editDesc,
        start_date: editStartDate || null
      })
      setIsEditModalOpen(false)
      setEditingJob(null)
      loadData()
    } catch (err) {
      alert('Error updating Job Posting.')
    } finally {
      setEditingSubmitting(false)
    }
  }

  const handleToggleStatus = async (job: Job) => {
    const newStatus = job.status === 'open' ? 'closed' : 'open'
    try {
      await updateJob(job.id, { status: newStatus })
      alert(`Job status updated to ${newStatus}`)
      loadData()
    } catch (err) {
      alert('Error updating job status.')
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
              Workspace Openings
            </span>
            <h1 className="font-signifier" style={{ fontSize: 'var(--text-heading-sm)', fontWeight: 500, color: 'var(--color-ink)', margin: '4px 0 0', lineHeight: 1.09 }}>
              Job Postings
            </h1>
          </div>
          <SteepButton 
            onClick={() => setIsModalOpen(true)}
            variant="primary"
          >
            Create Job
          </SteepButton>
        </div>

        {/* List of jobs */}
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
                <SteepCard 
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
                      {job.start_date && (
                        <span>Starts: {new Date(job.start_date).toLocaleDateString()}</span>
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
                        onClick={() => {
                          setEditingJob(job)
                          setEditTitle(job.title)
                          setEditDept(job.department)
                          setEditDesc(job.description || '')
                          setEditStartDate(job.start_date || '')
                          setIsEditModalOpen(true)
                        }}
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
                </SteepCard>
              )
            })}
          </div>
        )}

        {/* Modal for creating a job */}
        {isModalOpen && (
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
                    New Job Posting
                  </h2>
                  <SteepButton variant="ghost" onClick={() => setIsModalOpen(false)} style={{ padding: 4 }}>✕</SteepButton>
                </div>

                <form onSubmit={handleSubmit}>
                  <SteepInput 
                    id="job-title"
                    required
                    label="Job Title"
                    value={title}
                    onChange={e => setTitle(e.target.value)}
                    placeholder="e.g. Lead Frontend Engineer"
                  />

                  <SteepInput 
                    id="job-dept"
                    label="Department"
                    select
                    options={['Engineering', 'Product', 'Design', 'Operations', 'Sales', 'Marketing'].map(d => ({ value: d, label: d }))}
                    value={dept}
                    onChange={e => setDept(e.target.value)}
                  />

                  <SteepInput 
                    id="job-desc"
                    required
                    textarea
                    label="Description"
                    value={desc}
                    onChange={e => setDesc(e.target.value)}
                    placeholder="Provide role description and key skills requirements..."
                    style={{ minHeight: '100px' }}
                  />

                  <SteepInput 
                    id="job-start"
                    type="date"
                    label="Start Date (Optional)"
                    value={startDate}
                    onChange={e => setStartDate(e.target.value)}
                  />

                  <div style={{ display: 'flex', gap: 12, justifyContent: 'flex-end', marginTop: 24 }}>
                    <SteepButton 
                      type="button" 
                      onClick={() => setIsModalOpen(false)}
                      variant="secondary" 
                    >
                      Cancel
                    </SteepButton>
                    <SteepButton 
                      type="submit" 
                      disabled={submitting}
                      variant="primary" 
                    >
                      {submitting ? 'Creating...' : 'Create Job'}
                    </SteepButton>
                  </div>
                </form>
              </SteepCard>
            </div>
          </div>
        )}

        {/* Modal for editing a job */}
        {isEditModalOpen && (
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
                    Edit Job Posting
                  </h2>
                  <SteepButton variant="ghost" onClick={() => { setIsEditModalOpen(false); setEditingJob(null); }} style={{ padding: 4 }}>✕</SteepButton>
                </div>

                <form onSubmit={handleEditSubmit}>
                  <SteepInput 
                    id="edit-job-title"
                    required
                    label="Job Title"
                    value={editTitle}
                    onChange={e => setEditTitle(e.target.value)}
                    placeholder="e.g. Lead Frontend Engineer"
                  />

                  <SteepInput 
                    id="edit-job-dept"
                    label="Department"
                    select
                    options={['Engineering', 'Product', 'Design', 'Operations', 'Sales', 'Marketing'].map(d => ({ value: d, label: d }))}
                    value={editDept}
                    onChange={e => setEditDept(e.target.value)}
                  />

                  <SteepInput 
                    id="edit-job-desc"
                    required
                    textarea
                    label="Description"
                    value={editDesc}
                    onChange={e => setEditDesc(e.target.value)}
                    placeholder="Provide role description and key skills requirements..."
                    style={{ minHeight: '100px' }}
                  />

                  <SteepInput 
                    id="edit-job-start"
                    type="date"
                    label="Start Date (Optional)"
                    value={editStartDate}
                    onChange={e => setEditStartDate(e.target.value)}
                  />

                  <div style={{ display: 'flex', gap: 12, justifyContent: 'flex-end', marginTop: 24 }}>
                    <SteepButton 
                      type="button" 
                      onClick={() => { setIsEditModalOpen(false); setEditingJob(null); }}
                      variant="secondary" 
                    >
                      Cancel
                    </SteepButton>
                    <SteepButton 
                      type="submit" 
                      disabled={editingSubmitting}
                      variant="primary" 
                    >
                      {editingSubmitting ? 'Saving...' : 'Save Changes'}
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
