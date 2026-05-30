import { useState, useEffect, useRef, useCallback } from 'react'
import AppLayout from '../components/AppLayout'
import CandidateDrawer from '../components/CandidateDrawer'
import {
  recruitCandidate,
  fetchJobs,
  fetchApplications,
  createJob,
  createApplication,
  updateApplicationStatus,
  fetchCompany,
  type RecruitResult,
  type Job,
  type Application,
  type Company,
} from '../api'
import { scoreClass, decisionBadge } from '../utils/score'
import { checkHealth, formatApiError } from '../utils/apiError'

const STEPS = [
  'Parsing resume…',
  'Screening…',
  'Scoring…',
  'Making decision…',
  'Finalizing…',
]

type DrawerTab = 'overview' | 'screening' | 'communication' | 'onboarding'

export default function Dashboard() {
  const [files, setFiles] = useState<File[]>([])
  const [jobRole, setJobRole] = useState('')
  const [department, setDepartment] = useState('Engineering')
  const [startDate, setStartDate] = useState('')
  const [jobDesc, setJobDesc] = useState('')

  const [isProcessing, setIsProcessing] = useState(false)
  const [processingStep, setProcessingStep] = useState(0)
  const [results, setResults] = useState<RecruitResult[]>([])
  const [failedCount, setFailedCount] = useState(0)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [setupWarning, setSetupWarning] = useState<string | null>(null)

  const [company, setCompany] = useState<Company | null>(null)
  const [jobs, setJobs] = useState<Job[]>([])
  const [applications, setApplications] = useState<Application[]>([])
  const [selectedJobId, setSelectedJobId] = useState<string>('')

  const [selectedCandidate, setSelectedCandidate] = useState<RecruitResult | null>(null)
  const [drawerTab, setDrawerTab] = useState<DrawerTab>('overview')

  const fileInputRef = useRef<HTMLInputElement>(null)

  const loadPlatformData = useCallback(async () => {
    try {
      const [co, jobList, appList] = await Promise.all([
        fetchCompany(),
        fetchJobs(),
        fetchApplications(),
      ])
      setCompany(co)
      setJobs(jobList)
      setApplications(appList)
    } catch {
      /* auth or network — handled elsewhere */
    }
  }, [])

  useEffect(() => {
    loadPlatformData()
  }, [loadPlatformData])

  useEffect(() => {
    checkHealth().then((health) => {
      if (!health) {
        setSetupWarning(
          'Backend is not running. From the project root: docker compose up -d && python -m uvicorn backend.server:app --reload --port 8000',
        )
      } else if (!health.database_connected) {
        setSetupWarning(
          'Database is not connected. Run: docker compose up -d && alembic upgrade head',
        )
      } else if (!health.groq_api_key_configured) {
        setSetupWarning(
          'GROQ_API_KEY is not set. AI pipeline will fail until you add it to .env',
        )
      } else {
        setSetupWarning(null)
      }
    })
  }, [])

  useEffect(() => {
    if (!isProcessing) return
    const interval = setInterval(() => {
      setProcessingStep((prev) => (prev < STEPS.length - 1 ? prev + 1 : prev))
    }, 3000)
    return () => clearInterval(interval)
  }, [isProcessing])

  const addPdfFiles = (incoming: File[]) => {
    const pdfs = incoming.filter((f) => f.type === 'application/pdf' || f.name.toLowerCase().endsWith('.pdf'))
    if (pdfs.length < incoming.length) {
      setErrorMessage('Only PDF files are accepted. Non-PDF files were skipped.')
    } else {
      setErrorMessage(null)
    }
    if (pdfs.length) setFiles((prev) => [...prev, ...pdfs])
  }

  const handleFileDrop = (e: React.DragEvent) => {
    e.preventDefault()
    if (e.dataTransfer.files?.length) {
      addPdfFiles(Array.from(e.dataTransfer.files))
    }
  }

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.length) {
      addPdfFiles(Array.from(e.target.files))
      e.target.value = ''
    }
  }

  const removeFile = (idx: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== idx))
  }

  const applyJobToForm = (job: Job) => {
    setJobRole(job.title)
    setDepartment(job.department)
    setJobDesc(job.description)
    if (job.start_date) setStartDate(job.start_date)
  }

  const handleJobSelect = (jobId: string) => {
    setSelectedJobId(jobId)
    const job = jobs.find(j => j.id === jobId)
    if (job) applyJobToForm(job)
  }

  const persistApplication = async (result: RecruitResult, jobId: string) => {
    const decision = result.decision?.decision ?? 'REJECT'
    const statusMap = {
      HIRE: 'hired',
      INTERVIEW: 'interview',
      REJECT: 'rejected',
    } as const
    const app = await createApplication({
      job_id: jobId,
      candidate_name: result.candidate?.name ?? 'Unknown',
      candidate_email: result.candidate?.email ?? `unknown-${Date.now()}@example.com`,
      candidate_phone: result.candidate?.phone,
      source: 'pipeline',
    })
    await updateApplicationStatus(app.id, statusMap[decision] ?? 'screening')
  }

  const handleRunPipeline = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!files.length) return

    setIsProcessing(true)
    setProcessingStep(0)
    setResults([])
    setSelectedCandidate(null)
    setFailedCount(0)
    setErrorMessage(null)

    try {
      let jobId = selectedJobId
      if (!jobId) {
        const job = await createJob({
          title: jobRole,
          department,
          description: jobDesc,
          status: 'open',
          start_date: startDate || null,
        })
        jobId = job.id
        setSelectedJobId(job.id)
        setJobs(prev => [job, ...prev])
      }

      const promises = files.map((file) => {
        const fd = new FormData()
        fd.append('file', file)
        fd.append('job_role', jobRole)
        fd.append('department', department)
        fd.append('start_date', startDate)
        fd.append('job_description', jobDesc)
        return recruitCandidate(fd)
      })

      const outcomes = await Promise.allSettled(promises)
      const successful: RecruitResult[] = []
      let failed = 0
      let firstError: string | null = null

      outcomes.forEach((outcome) => {
        if (outcome.status === 'fulfilled' && outcome.value.success) {
          successful.push(outcome.value)
        } else {
          failed += 1
          if (!firstError && outcome.status === 'rejected') {
            firstError = formatApiError(outcome.reason)
          }
        }
      })

      successful.sort((a, b) => (b.scoring?.total_score || 0) - (a.scoring?.total_score || 0))
      setResults(successful)
      setFailedCount(failed)

      for (const result of successful) {
        try {
          await persistApplication(result, jobId)
        } catch {
          /* duplicate application etc. */
        }
      }
      await loadPlatformData()

      if (failed > 0 && successful.length === 0) {
        setErrorMessage(
          firstError ??
            `${failed} resume${failed > 1 ? 's' : ''} could not be processed. Check backend logs for details.`,
        )
      } else if (failed > 0 && successful.length > 0) {
        setErrorMessage(`${failed} of ${files.length} resumes failed. Showing ${successful.length} successful result${successful.length !== 1 ? 's' : ''}.`)
      }
    } catch (err) {
      setErrorMessage(formatApiError(err))
    } finally {
      setIsProcessing(false)
      setProcessingStep(STEPS.length - 1)
    }
  }

  const openCandidate = (result: RecruitResult) => {
    setSelectedCandidate(result)
    setDrawerTab('overview')
  }

  return (
    <AppLayout>
      <div className="dashboard-page container container--wide">
        <header style={{ marginBottom: 'var(--space-8)' }}>
          <h1 style={{ fontSize: 'var(--text-3xl)', fontWeight: 700, letterSpacing: '-0.02em', marginBottom: 'var(--space-2)' }}>
            Recruitment pipeline
          </h1>
          <p className="text-secondary" style={{ fontSize: 'var(--text-base)', maxWidth: '56ch' }}>
            {company ? `${company.name} — ` : ''}Configure the role, upload resumes, and run the AI workflow. Jobs and applications are saved to your workspace.
          </p>
        </header>

        {setupWarning && (
          <div className="banner banner--warning" style={{ marginBottom: 'var(--space-6)' }} role="status">
            {setupWarning}
          </div>
        )}

        {errorMessage && (
          <div className="banner banner--warning" style={{ marginBottom: 'var(--space-6)' }} role="alert">
            {errorMessage}
          </div>
        )}

        <div className="dashboard-grid">
          <aside className="dashboard-sidebar">
            <div className="card">
              <div className="card__header">
                <h2 style={{ fontSize: 'var(--text-base)', fontWeight: 700 }}>New run</h2>
                <p className="text-tertiary" style={{ fontSize: 'var(--text-xs)', marginTop: 4 }}>
                  Required fields marked on submit
                </p>
              </div>
              <div className="card__body">
                <form onSubmit={handleRunPipeline}>
                  <div
                    className="dropzone"
                    onDragOver={(e) => e.preventDefault()}
                    onDrop={handleFileDrop}
                    onClick={() => fileInputRef.current?.click()}
                    role="button"
                    tabIndex={0}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault()
                        fileInputRef.current?.click()
                      }
                    }}
                    aria-label="Upload PDF resumes"
                  >
                    <input
                      type="file"
                      multiple
                      accept=".pdf,application/pdf"
                      ref={fileInputRef}
                      className="sr-only"
                      onChange={handleFileSelect}
                    />
                    <svg
                      width="24"
                      height="24"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="var(--text-tertiary)"
                      strokeWidth="2"
                      style={{ marginBottom: 8 }}
                      aria-hidden="true"
                    >
                      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                      <polyline points="17 8 12 3 7 8" />
                      <line x1="12" y1="3" x2="12" y2="15" />
                    </svg>
                    <div style={{ fontWeight: 600, fontSize: 'var(--text-sm)' }}>Drop PDF resumes</div>
                    <div className="text-tertiary" style={{ fontSize: 'var(--text-xs)', marginTop: 4 }}>
                      or click to browse
                    </div>
                  </div>

                  {files.length > 0 && (
                    <ul className="file-list" aria-label="Uploaded files">
                      {files.map((file, idx) => (
                        <li key={`${file.name}-${idx}`} className="file-item">
                          <span className="file-item__name">{file.name}</span>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0 }}>
                            <span className="text-tertiary">{(file.size / 1024 / 1024).toFixed(1)} MB</span>
                            <button
                              type="button"
                              className="icon-btn"
                              onClick={(e) => {
                                e.stopPropagation()
                                removeFile(idx)
                              }}
                              aria-label={`Remove ${file.name}`}
                            >
                              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                <line x1="18" y1="6" x2="6" y2="18" />
                                <line x1="6" y1="6" x2="18" y2="18" />
                              </svg>
                            </button>
                          </div>
                        </li>
                      ))}
                    </ul>
                  )}

                  <div className="form-group">
                    <label className="form-label" htmlFor="saved-job">Saved job (optional)</label>
                    <select
                      id="saved-job"
                      className="form-select"
                      value={selectedJobId}
                      onChange={e => handleJobSelect(e.target.value)}
                    >
                      <option value="">Create new from form below</option>
                      {jobs.map(j => (
                        <option key={j.id} value={j.id}>
                          {j.title} · {j.department} ({j.status})
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="form-group">
                    <label className="form-label" htmlFor="job-role">Job role</label>
                    <input
                      id="job-role"
                      required
                      type="text"
                      className="form-input"
                      value={jobRole}
                      onChange={(e) => setJobRole(e.target.value)}
                      placeholder="Senior Software Engineer"
                    />
                  </div>

                  <div className="form-group">
                    <label className="form-label" htmlFor="department">Department</label>
                    <select
                      id="department"
                      className="form-select"
                      value={department}
                      onChange={(e) => setDepartment(e.target.value)}
                    >
                      {['Engineering', 'Product', 'Design', 'Sales', 'Marketing', 'HR', 'Operations', 'Finance'].map(
                        (d) => (
                          <option key={d}>{d}</option>
                        ),
                      )}
                    </select>
                  </div>

                  <div className="form-group">
                    <label className="form-label" htmlFor="start-date">Start date</label>
                    <input
                      id="start-date"
                      required
                      type="date"
                      className="form-input"
                      value={startDate}
                      onChange={(e) => setStartDate(e.target.value)}
                    />
                  </div>

                  <div className="form-group">
                    <label className="form-label" htmlFor="job-desc">Job description</label>
                    <textarea
                      id="job-desc"
                      required
                      className="form-textarea"
                      style={{ minHeight: 140 }}
                      value={jobDesc}
                      onChange={(e) => setJobDesc(e.target.value)}
                      placeholder="Paste requirements, responsibilities, and qualifications…"
                    />
                    <p className="form-hint">Used by screening and scoring agents for match analysis.</p>
                  </div>

                  <button
                    type="submit"
                    className="btn btn--primary btn--block"
                    disabled={isProcessing || files.length === 0}
                  >
                    {isProcessing ? 'Running pipeline…' : `Run pipeline${files.length ? ` (${files.length})` : ''}`}
                  </button>
                </form>
              </div>
            </div>
          </aside>

          <section aria-live="polite">
            {isProcessing ? (
              <>
                <h2 style={{ fontSize: 'var(--text-xl)', fontWeight: 600, marginBottom: 'var(--space-5)' }}>
                  Processing {files.length} candidate{files.length !== 1 ? 's' : ''}
                </h2>
                <div className="processing-grid">
                  {files.map((file, idx) => (
                    <article key={`${file.name}-${idx}`} className="processing-card">
                      <div className="spinner spinner--lg" aria-hidden="true" />
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div
                          style={{
                            fontWeight: 600,
                            fontSize: 'var(--text-sm)',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            whiteSpace: 'nowrap',
                          }}
                        >
                          {file.name}
                        </div>
                        <div className="text-accent" style={{ fontSize: 'var(--text-xs)', marginTop: 4 }}>
                          {STEPS[Math.min(processingStep, STEPS.length - 1)]}
                        </div>
                      </div>
                    </article>
                  ))}
                </div>
              </>
            ) : results.length > 0 ? (
              <>
                <div
                  style={{
                    display: 'flex',
                    flexWrap: 'wrap',
                    justifyContent: 'space-between',
                    alignItems: 'baseline',
                    gap: 'var(--space-3)',
                    marginBottom: 'var(--space-5)',
                  }}
                >
                  <h2 style={{ fontSize: 'var(--text-xl)', fontWeight: 600 }}>
                    {results.length} candidate{results.length !== 1 ? 's' : ''}
                    {failedCount > 0 && (
                      <span className="text-tertiary" style={{ fontWeight: 400, fontSize: 'var(--text-sm)', marginLeft: 8 }}>
                        ({failedCount} failed)
                      </span>
                    )}
                  </h2>
                  <span className="text-tertiary" style={{ fontSize: 'var(--text-sm)' }}>
                    Sorted by fit score
                  </span>
                </div>

                <div className="table-wrap">
                  <div className="table-scroll">
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th style={{ width: 56, textAlign: 'center' }}>#</th>
                          <th>Candidate</th>
                          <th style={{ textAlign: 'center' }}>Score</th>
                          <th>Decision</th>
                          <th>Skills</th>
                          <th>Fit</th>
                          <th>Exp.</th>
                          <th style={{ textAlign: 'right' }} />
                        </tr>
                      </thead>
                      <tbody>
                        {results.map((result, idx) => {
                          const score = result.scoring?.total_score ?? 0
                          const badge = decisionBadge(result.decision?.decision ?? 'REJECT')
                          const rank = idx + 1

                          return (
                            <tr key={`${result.candidate?.email ?? idx}-${idx}`} className={rank === 1 ? 'row-top' : ''}>
                              <td style={{ textAlign: 'center', fontWeight: 600, color: 'var(--text-tertiary)' }}>
                                {rank}
                              </td>
                              <td>
                                <div style={{ fontWeight: 600 }}>{result.candidate?.name ?? 'Unknown'}</div>
                                <div className="text-tertiary" style={{ fontSize: 'var(--text-xs)' }}>
                                  {result.candidate?.email ?? 'No email'}
                                </div>
                              </td>
                              <td style={{ textAlign: 'center' }}>
                                <span className={`score-ring ${scoreClass(score)}`}>{score}</span>
                              </td>
                              <td>
                                <span className={`badge ${badge.className}`}>{badge.label}</span>
                              </td>
                              <td>
                                <div style={{ fontWeight: 500 }}>{result.screening?.skills_match_percentage ?? 0}%</div>
                                <div className="text-tertiary" style={{ fontSize: 11 }}>match</div>
                              </td>
                              <td style={{ fontSize: 'var(--text-sm)' }}>
                                {result.scoring?.overall_fit ?? '—'}
                              </td>
                              <td>{result.candidate?.experience_years ?? 0} yrs</td>
                              <td style={{ textAlign: 'right' }}>
                                <button
                                  type="button"
                                  className="btn btn--secondary btn--sm"
                                  onClick={() => openCandidate(result)}
                                >
                                  Details
                                </button>
                              </td>
                            </tr>
                          )
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>
              </>
            ) : (
              <div className="empty-state">
                <svg className="empty-state__icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                  <polyline points="14 2 14 8 20 8" />
                  <line x1="12" y1="18" x2="12" y2="12" />
                  <line x1="9" y1="15" x2="15" y2="15" />
                </svg>
                <h3 className="empty-state__title">No results yet</h3>
                <p className="empty-state__desc">
                  Upload PDF resumes and complete the job form to run your first recruitment pipeline.
                </p>
              </div>
            )}
          </section>
        </div>

        {applications.length > 0 && (
          <section style={{ marginTop: 'var(--space-12)' }}>
            <h2 style={{ fontSize: 'var(--text-xl)', fontWeight: 600, marginBottom: 'var(--space-5)' }}>
              Saved applications ({applications.length})
            </h2>
            <div className="table-wrap">
              <div className="table-scroll">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Candidate</th>
                      <th>Job</th>
                      <th>Status</th>
                      <th>Source</th>
                      <th>Applied</th>
                    </tr>
                  </thead>
                  <tbody>
                    {applications.map(app => (
                      <tr key={app.id}>
                        <td>
                          <div style={{ fontWeight: 600 }}>{app.candidate?.full_name ?? '—'}</div>
                          <div className="text-tertiary" style={{ fontSize: 'var(--text-xs)' }}>
                            {app.candidate?.email}
                          </div>
                        </td>
                        <td>{app.job?.title ?? '—'}</td>
                        <td>
                          <span className="badge badge--neutral">{app.status}</span>
                        </td>
                        <td className="text-secondary">{app.source}</td>
                        <td className="text-tertiary" style={{ fontSize: 'var(--text-sm)' }}>
                          {new Date(app.created_at).toLocaleDateString()}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </section>
        )}
      </div>

      {selectedCandidate && (
        <CandidateDrawer
          candidate={selectedCandidate}
          tab={drawerTab}
          onTabChange={setDrawerTab}
          onClose={() => setSelectedCandidate(null)}
        />
      )}
    </AppLayout>
  )
}
