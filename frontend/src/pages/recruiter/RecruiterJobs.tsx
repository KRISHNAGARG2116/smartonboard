import { useState, useEffect, useCallback } from 'react'
import AppLayout from '../../components/AppLayout'
import { fetchJobs, createJob, type Job } from '../../api'

export default function RecruiterJobs() {
  const [jobs, setJobs] = useState<Job[]>([])
  const [loading, setLoading] = useState(true)
  const [isModalOpen, setIsModalOpen] = useState(false)
  
  // Form State
  const [title, setTitle] = useState('')
  const [dept, setDept] = useState('Engineering')
  const [desc, setDesc] = useState('')
  const [startDate, setStartDate] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const loadJobs = useCallback(async () => {
    setLoading(true)
    try {
      const jobList = await fetchJobs()
      setJobs(jobList)
    } catch (err) {
      console.error('Error fetching jobs:', err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadJobs()
  }, [loadJobs])

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
      loadJobs()
    } catch (err) {
      alert('Error creating Job Posting.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <AppLayout>
      <div className="container" style={{ padding: 'var(--space-6) 0 var(--space-12)' }}>
        {/* Header */}
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          borderBottom: '1px solid var(--border)',
          paddingBottom: 'var(--space-6)',
          marginBottom: 'var(--space-6)'
        }}>
          <div>
            <span style={{ fontSize: 10, fontWeight: 500, color: 'var(--text-secondary)', letterSpacing: '0.05em', textTransform: 'uppercase' }}>
              Workspace Openings
            </span>
            <h1 style={{ fontSize: '29px', fontWeight: 500, letterSpacing: '-0.02em', color: 'var(--text)', margin: '4px 0 0', lineHeight: 1.09 }}>
              Job Postings
            </h1>
          </div>
          <button 
            onClick={() => setIsModalOpen(true)}
            className="btn btn--primary" 
            style={{ borderRadius: 'var(--radius-buttons)' }}
          >
            Create Job
          </button>
        </div>

        {/* List of jobs */}
        {loading ? (
          <div style={{ padding: 'var(--space-12) 0', textAlign: 'center', color: 'var(--text-secondary)' }}>
            Loading active job postings...
          </div>
        ) : jobs.length === 0 ? (
          <div style={{
            padding: 'var(--space-12)',
            textAlign: 'center',
            border: '1px solid var(--border)',
            borderRadius: 12,
            color: 'var(--text-secondary)'
          }}>
            No active job postings. Click "Create Job" to post your first opening.
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
            {jobs.map((job) => (
              <div 
                key={job.id}
                style={{
                  border: '1px solid var(--color-cork-shadow)',
                  borderRadius: 12,
                  padding: 'var(--space-4)',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center'
                }}
              >
                <div>
                  <h3 style={{ fontSize: '18px', fontWeight: 500, color: 'var(--text)', margin: 0 }}>
                    {job.title}
                  </h3>
                  <div style={{ display: 'flex', gap: 12, marginTop: 4, fontSize: 12, color: 'var(--text-secondary)' }}>
                    <span>{job.department}</span>
                    <span>&bull;</span>
                    <span>Status: {job.status}</span>
                  </div>
                </div>
                <div style={{ fontSize: 14, color: 'var(--text-secondary)' }}>
                  Active Applicants: <strong style={{ color: 'var(--text)' }}>Open</strong>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Modal for creating a job */}
        {isModalOpen && (
          <div style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0, 0, 0, 0.75)',
            display: 'grid',
            placeItems: 'center',
            zIndex: 100,
            padding: 24
          }}>
            <div style={{
              background: 'var(--bg)',
              border: '1px solid var(--border)',
              borderRadius: 12,
              padding: 32,
              maxWidth: 480,
              width: '100%',
              boxSizing: 'border-box'
            }}>
              <h2 style={{ fontSize: 24, fontWeight: 500, margin: '0 0 24px', color: 'var(--text)' }}>
                New Job Posting
              </h2>

              <form onSubmit={handleSubmit}>
                <div style={{ marginBottom: 20 }}>
                  <label htmlFor="job-title" style={{ display: 'block', fontSize: 10, fontWeight: 500, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 8 }}>
                    Job Title
                  </label>
                  <input 
                    id="job-title"
                    required
                    value={title}
                    onChange={e => setTitle(e.target.value)}
                    placeholder="e.g. Lead Frontend Engineer"
                    style={{
                      width: '100%',
                      background: 'transparent',
                      border: 'none',
                      borderBottom: '1px solid var(--border)',
                      borderRadius: 0,
                      padding: '8px 0',
                      fontSize: 15,
                      color: 'var(--text)',
                      outline: 'none'
                    }}
                  />
                </div>

                <div style={{ marginBottom: 20 }}>
                  <label htmlFor="job-dept" style={{ display: 'block', fontSize: 10, fontWeight: 500, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 8 }}>
                    Department
                  </label>
                  <select 
                    id="job-dept"
                    value={dept}
                    onChange={e => setDept(e.target.value)}
                    style={{
                      width: '100%',
                      background: 'transparent',
                      border: 'none',
                      borderBottom: '1px solid var(--border)',
                      borderRadius: 0,
                      padding: '8px 0',
                      fontSize: 15,
                      color: 'var(--text)',
                      outline: 'none',
                      cursor: 'pointer'
                    }}
                  >
                    <option value="Engineering" style={{ background: 'var(--bg)' }}>Engineering</option>
                    <option value="Product" style={{ background: 'var(--bg)' }}>Product</option>
                    <option value="Design" style={{ background: 'var(--bg)' }}>Design</option>
                    <option value="Operations" style={{ background: 'var(--bg)' }}>Operations</option>
                  </select>
                </div>

                <div style={{ marginBottom: 20 }}>
                  <label htmlFor="job-desc" style={{ display: 'block', fontSize: 10, fontWeight: 500, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 8 }}>
                    Description
                  </label>
                  <textarea 
                    id="job-desc"
                    required
                    value={desc}
                    onChange={e => setDesc(e.target.value)}
                    placeholder="Provide role description and key skills requirements..."
                    rows={4}
                    style={{
                      width: '100%',
                      background: 'transparent',
                      border: '1px solid var(--border)',
                      borderRadius: 12,
                      padding: '12px',
                      fontSize: 14,
                      color: 'var(--text)',
                      outline: 'none',
                      boxSizing: 'border-box',
                      resize: 'vertical'
                    }}
                  />
                </div>

                <div style={{ marginBottom: 28 }}>
                  <label htmlFor="job-start" style={{ display: 'block', fontSize: 10, fontWeight: 500, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 8 }}>
                    Start Date (Optional)
                  </label>
                  <input 
                    id="job-start"
                    type="date"
                    value={startDate}
                    onChange={e => setStartDate(e.target.value)}
                    style={{
                      width: '100%',
                      background: 'transparent',
                      border: 'none',
                      borderBottom: '1px solid var(--border)',
                      borderRadius: 0,
                      padding: '8px 0',
                      fontSize: 15,
                      color: 'var(--text)',
                      outline: 'none'
                    }}
                  />
                </div>

                <div style={{ display: 'flex', gap: 12, justifyContent: 'flex-end' }}>
                  <button 
                    type="button" 
                    onClick={() => setIsModalOpen(false)}
                    className="btn btn--secondary" 
                    style={{ borderRadius: 'var(--radius-buttons)' }}
                  >
                    Cancel
                  </button>
                  <button 
                    type="submit" 
                    disabled={submitting}
                    className="btn btn--primary" 
                    style={{ borderRadius: 'var(--radius-buttons)', opacity: submitting ? 0.6 : 1 }}
                  >
                    {submitting ? 'Creating...' : 'Create Job'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </div>
    </AppLayout>
  )
}
