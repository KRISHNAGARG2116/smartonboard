import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import CandidateLayout from '../components/CandidateLayout'
import { ListRowSkeleton } from '../components/Skeletons'
import EmptyState from '../components/EmptyState'

const containerVariants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: {
      staggerChildren: 0.04
    }
  }
}

const itemVariants = {
  hidden: { opacity: 0, y: 10 },
  show: { opacity: 1, y: 0, transition: { duration: 0.25, ease: 'easeOut' as any } }
}
import {
  fetchJobFeed,
  applyToJob,
  fetchCandidateResumes,
  fetchCandidateProfile,
  type JobFeedItem,
  type CandidateResume
} from '../api'

export default function CandidateJobFeed() {
  const [jobs, setJobs] = useState<JobFeedItem[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const limit = 10
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [profile, setProfile] = useState<{ email_verified: boolean; phone_verified: boolean } | null>(null)

  // Drawer / Selection state
  const [selectedJob, setSelectedJob] = useState<JobFeedItem | null>(null)
  const [resumes, setResumes] = useState<CandidateResume[]>([])
  const [resumesLoading, setResumesLoading] = useState(false)
  const [selectedResumeId, setSelectedResumeId] = useState<string>('')
  
  // Submit state
  const [applying, setApplying] = useState(false)
  const [applySuccess, setApplySuccess] = useState<boolean>(false)
  const [applyError, setApplyError] = useState<string | null>(null)

  // Track applied jobs in current session to immediately update UI state
  const [appliedJobIds, setAppliedJobIds] = useState<Set<string>>(new Set())

  // Load feed
  const loadJobFeed = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchJobFeed(page, limit)
      setJobs(data.results)
      setTotal(data.total)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to retrieve job feed. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadJobFeed()
  }, [page])

  useEffect(() => {
    fetchCandidateProfile()
      .then((data) => {
        if (data && data.profile) {
          setProfile(data.profile)
        }
      })
      .catch(() => {})
  }, [])

  // Load resumes when drawer opens
  useEffect(() => {
    if (selectedJob) {
      setResumesLoading(true)
      setApplySuccess(false)
      setApplyError(null)
      fetchCandidateResumes()
        .then((data) => {
          setResumes(data)
          if (data.length > 0) {
            // Pre-select active resume, else fallback to first resume
            const activeResume = data.find(r => r.is_active)
            setSelectedResumeId(activeResume ? activeResume.id : data[0].id)
          } else {
            setSelectedResumeId('')
          }
        })
        .catch(() => {})
        .finally(() => setResumesLoading(false))
    }
  }, [selectedJob])

  const handleApply = async () => {
    if (!selectedJob || !selectedResumeId) return
    if (profile && (!profile.email_verified || !profile.phone_verified)) {
      setApplyError("Verification Required: You must verify your email and phone number to apply to jobs.")
      return
    }
    setApplying(true)
    setApplyError(null)
    try {
      const res = await applyToJob(selectedJob.id, selectedResumeId)
      if (res.success) {
        setApplySuccess(true)
        setAppliedJobIds(prev => {
          const next = new Set(prev)
          next.add(selectedJob.id)
          return next
        })
      }
    } catch (err: any) {
      setApplyError(err.response?.data?.detail || 'Failed to submit application. Please try again.')
    } finally {
      setApplying(false)
    }
  }

  // Helper to determine match badge colors/styles dynamically
  const getMatchStyles = (score: number, isNoSkills: boolean) => {
    if (isNoSkills || score === 100) {
      return {
        border: '1px solid var(--color-warm-cream)',
        background: 'transparent',
        color: 'var(--text)',
        label: '100% Match'
      }
    } else if (score >= 80) {
      return {
        border: '1px solid var(--color-warm-cream)',
        background: 'transparent',
        color: 'var(--text)',
        label: `${score}% Match`
      }
    } else if (score >= 50) {
      return {
        border: '1px solid var(--color-cork-shadow)',
        background: 'transparent',
        color: 'var(--text-secondary)',
        label: `${score}% Match`
      }
    } else {
      return {
        border: '1px solid var(--color-cork-shadow)',
        background: 'transparent',
        color: 'var(--text-secondary)',
        label: `${score}% Match`
      }
    }
  }

  const totalPages = Math.ceil(total / limit)

  return (
    <CandidateLayout>
      <div className="container" style={{ padding: 'var(--space-6) 0 var(--space-12)' }}>
        <div style={{ maxWidth: '960px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: 'var(--space-6)' }}>
          
          {/* Header Dashboard section */}
          <div className="card card__body" style={{ background: 'transparent', borderRadius: '12px', border: '1px dashed var(--color-cork-shadow)' }}>
            <h3 style={{ fontSize: '24px', fontWeight: 500, marginBottom: 'var(--space-2)', color: 'var(--text)', lineHeight: 1.1 }}>Explore Openings</h3>
            <p style={{ color: 'var(--text-secondary)', fontSize: '14px', marginBottom: 0, lineHeight: 1.33 }}>
              Discover active job opportunities matching your background. Review applicability percentages driven by your active resume profile.
            </p>
          </div>

          {error && (
            <div className="card card__body" style={{ border: '1px solid var(--danger)', background: 'var(--danger-bg)', color: 'var(--text)', borderRadius: 'var(--radius-md)' }}>
              <strong>Error:</strong> {error}
            </div>
          )}

          {/* Jobs Feed list */}
          {loading ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
              <ListRowSkeleton />
              <ListRowSkeleton />
              <ListRowSkeleton />
              <ListRowSkeleton />
            </div>
          ) : jobs.length === 0 ? (
            <EmptyState
              type="jobs"
              title="No Jobs In Feed"
              description="No active job postings are available on the platform right now. Check back soon for new opportunities."
            />
          ) : (
            <motion.div
              variants={containerVariants}
              initial="hidden"
              animate="show"
              style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}
            >
              {jobs.map((job) => {
                const isApplied = appliedJobIds.has(job.id)
                // Determine if job has no skills configuration (matching + missing are both empty)
                const isNoSkills = job.matching_skills.length === 0 && job.missing_skills.length === 0
                const matchStyle = getMatchStyles(job.applicability_score, isNoSkills)

                return (
                  <motion.div 
                    key={job.id} 
                    variants={itemVariants}
                    whileHover={{ y: -2, borderColor: 'var(--color-warm-cream)' }}
                    transition={{ duration: 0.2, ease: 'easeOut' }}
                    className="card card__body"
                    style={{ 
                      display: 'flex', 
                      justifyContent: 'space-between', 
                      alignItems: 'center', 
                      borderRadius: '12px',
                      border: '1px dashed var(--color-cork-shadow)',
                      cursor: 'pointer'
                    }}
                    onClick={() => setSelectedJob(job)}
                  >
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)', minWidth: 0, flex: 1, paddingRight: 'var(--space-4)' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)', flexWrap: 'wrap' }}>
                        <h4 style={{ fontSize: 'var(--text-base)', fontWeight: 700, margin: 0 }}>{job.title}</h4>
                        <span 
                          style={{ 
                            fontSize: '10px', 
                            fontWeight: 750, 
                            padding: '3px 8px', 
                            borderRadius: '999px',
                            border: matchStyle.border,
                            background: matchStyle.background,
                            color: matchStyle.color
                          }}
                        >
                          {matchStyle.label}
                        </span>
                        {isApplied && (
                          <span style={{ fontSize: '10px', fontWeight: 500, padding: '3px 8px', borderRadius: '999px', background: 'transparent', color: 'var(--text)', border: '1px solid var(--color-warm-cream)' }}>
                            Applied
                          </span>
                        )}
                      </div>
                      <p style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-xs)', margin: 0 }}>
                        {job.company_name} · <strong>{job.department}</strong>
                      </p>
                      
                      {/* Skills Preview */}
                      {!isNoSkills && (
                        <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', marginTop: 'var(--space-2)' }}>
                          {job.matching_skills.slice(0, 3).map((skill, idx) => (
                            <span 
                              key={idx} 
                              style={{ 
                                fontSize: '10px', 
                                padding: '2px 8px', 
                                borderRadius: '6px', 
                                background: 'transparent', 
                                color: 'var(--text)',
                                border: '1px solid var(--color-cork-shadow)',
                                fontWeight: 500
                              }}
                            >
                              ✓ {skill}
                            </span>
                          ))}
                          {job.missing_skills.slice(0, 2).map((skill, idx) => (
                            <span 
                              key={idx} 
                              style={{ 
                                fontSize: '10px', 
                                padding: '2px 8px', 
                                borderRadius: '6px', 
                                background: 'transparent', 
                                color: 'var(--text-secondary)',
                                border: '1px solid var(--color-cork-shadow)',
                                fontWeight: 400
                              }}
                            >
                              ? {skill}
                            </span>
                          ))}
                          {(job.matching_skills.length > 3 || job.missing_skills.length > 2) && (
                            <span style={{ fontSize: '10px', color: 'var(--text-tertiary)', padding: '2px 4px' }}>
                              +{job.matching_skills.length + job.missing_skills.length - 5} more
                            </span>
                          )}
                        </div>
                      )}
                    </div>

                    <div style={{ flexShrink: 0 }}>
                      <button 
                        type="button" 
                        className="btn btn--secondary btn--sm" 
                        style={{ borderRadius: '22.5px', padding: '8px 16px', fontWeight: 500 }}
                        onClick={(e) => {
                          e.stopPropagation()
                          setSelectedJob(job)
                        }}
                      >
                        Details →
                      </button>
                    </div>
                  </motion.div>
                )
              })}
            </motion.div>
          )}

          {/* Pagination controls */}
          {!loading && totalPages > 1 && (
            <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 'var(--space-4)', marginTop: 'var(--space-4)' }}>
              <button
                type="button"
                className="btn btn--secondary btn--sm"
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
                style={{ borderRadius: '22.5px' }}
              >
                ← Previous
              </button>
              <span style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)', fontWeight: 550 }}>
                Page {page} of {totalPages}
              </span>
              <button
                type="button"
                className="btn btn--secondary btn--sm"
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                style={{ borderRadius: '22.5px' }}
              >
                Next →
              </button>
            </div>
          )}

        </div>
      </div>

      {/* Slide-out Job Details Drawer */}
      {selectedJob && (
        <>
          <div 
            onClick={() => setSelectedJob(null)}
            style={{
              position: 'fixed',
              inset: 0,
              background: 'rgba(16,9,4,0.7)',
              zIndex: 999,
              transition: 'opacity var(--duration-normal)'
            }}
          />
          <aside
            role="dialog"
            aria-modal="true"
            aria-labelledby="drawer-job-title"
            style={{
              position: 'fixed',
              top: 0,
              right: 0,
              bottom: 0,
              width: 'min(560px, 100vw)',
              background: 'var(--bg)',
              borderLeft: '1px solid var(--color-cork-shadow)',
              display: 'flex',
              flexDirection: 'column',
              zIndex: 1000,
              boxShadow: 'none',
              overflow: 'hidden'
            }}
          >
            {/* Drawer Header */}
            <div 
              style={{ 
                padding: 'var(--space-6)', 
                borderBottom: '1px dashed var(--color-cork-shadow)', 
                display: 'flex', 
                justifyContent: 'space-between', 
                alignItems: 'flex-start' 
              }}
            >
              <div>
                <h2 id="drawer-job-title" style={{ fontSize: 'var(--text-lg)', fontWeight: 800, letterSpacing: '-0.02em', margin: 0 }}>
                  {selectedJob.title}
                </h2>
                <p style={{ fontSize: 'var(--text-xs)', color: 'var(--text-secondary)', marginTop: '4px', margin: 0 }}>
                  {selectedJob.company_name} · <strong>{selectedJob.department}</strong>
                </p>
              </div>
              <button
                type="button"
                className="icon-btn"
                onClick={() => setSelectedJob(null)}
                style={{ 
                  border: '1px solid var(--color-cork-shadow)', 
                  borderRadius: '50%', 
                  width: '32px', 
                  height: '32px', 
                  display: 'grid', 
                  placeItems: 'center',
                  background: 'transparent',
                  color: 'var(--text)'
                }}
                aria-label="Close Job Drawer"
              >
                ✕
              </button>
            </div>

            {/* Drawer Body Scroll Content */}
            <div style={{ flex: 1, overflowY: 'auto', padding: 'var(--space-6)', display: 'flex', flexDirection: 'column', gap: 'var(--space-6)' }}>
              
              {/* Applicability Ring Block */}
              <div 
                style={{ 
                  display: 'flex', 
                  alignItems: 'center', 
                  gap: 'var(--space-5)', 
                  padding: 'var(--space-4)', 
                  background: 'transparent', 
                  borderRadius: '12px', 
                  border: '1px dashed var(--color-cork-shadow)' 
                }}
              >
                {/* Visual Circular Ring */}
                <div 
                  style={{
                    position: 'relative',
                    width: '60px',
                    height: '60px',
                    borderRadius: '50%',
                    background: `conic-gradient(var(--color-warm-cream) ${selectedJob.matching_skills.length === 0 && selectedJob.missing_skills.length === 0 ? 100 : selectedJob.applicability_score}%, var(--color-cork-shadow) 0)`,
                    display: 'grid',
                    placeItems: 'center',
                    flexShrink: 0
                  }}
                >
                  <div 
                    style={{
                      position: 'absolute',
                      inset: '5px',
                      borderRadius: '50%',
                      background: 'var(--bg)',
                      display: 'grid',
                      placeItems: 'center',
                      fontSize: 'var(--text-sm)',
                      fontWeight: 800
                    }}
                  >
                    {selectedJob.matching_skills.length === 0 && selectedJob.missing_skills.length === 0 ? 100 : selectedJob.applicability_score}%
                  </div>
                </div>
                
                <div>
                  <h4 style={{ fontSize: 'var(--text-sm)', fontWeight: 750, margin: 0 }}>Personalized Applicability Fit</h4>
                  <p style={{ fontSize: 'var(--text-xs)', color: 'var(--text-secondary)', marginTop: '2px', margin: 0, lineHeight: 1.3 }}>
                    {selectedJob.matching_skills.length === 0 && selectedJob.missing_skills.length === 0 ? (
                      'This job has no specific skills configuration. All candidates match at 100%.'
                    ) : (
                      `Your resume matches ${selectedJob.matching_skills.length} of ${selectedJob.matching_skills.length + selectedJob.missing_skills.length} identified requirements.`
                    )}
                  </p>
                </div>
              </div>

              {/* Skills Analysis */}
              {(selectedJob.matching_skills.length > 0 || selectedJob.missing_skills.length > 0) && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
                  <h4 style={{ fontSize: 'var(--text-sm)', fontWeight: 750, textTransform: 'uppercase', letterSpacing: '0.04em', color: 'var(--text-secondary)', margin: 0 }}>
                    Skills Matching Audit
                  </h4>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: 'var(--space-3)' }}>
                    
                    {/* Matching */}
                    {selectedJob.matching_skills.length > 0 && (
                      <div style={{ border: '1px dashed var(--color-cork-shadow)', borderRadius: '12px', padding: 'var(--space-3)' }}>
                        <span style={{ fontSize: '11px', fontWeight: 750, color: 'var(--success)', display: 'block', marginBottom: '8px' }}>
                          ✓ Matching Skills ({selectedJob.matching_skills.length})
                        </span>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                          {selectedJob.matching_skills.map((skill, idx) => (
                            <span 
                              key={idx} 
                              style={{ 
                                fontSize: '10px', 
                                padding: '2px 8px', 
                                borderRadius: '6px', 
                                background: 'var(--success-bg)', 
                                color: 'var(--success)',
                                fontWeight: 550
                              }}
                            >
                              {skill}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Missing */}
                    {selectedJob.missing_skills.length > 0 && (
                      <div style={{ border: '1px dashed var(--color-cork-shadow)', borderRadius: '12px', padding: 'var(--space-3)' }}>
                        <span style={{ fontSize: '11px', fontWeight: 750, color: 'var(--text-secondary)', display: 'block', marginBottom: '8px' }}>
                          ? Missing Skills ({selectedJob.missing_skills.length})
                        </span>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                          {selectedJob.missing_skills.map((skill, idx) => (
                            <span 
                              key={idx} 
                              style={{ 
                                fontSize: '10px', 
                                padding: '2px 8px', 
                                borderRadius: '6px', 
                                background: 'transparent', 
                                color: 'var(--text-secondary)',
                                border: '1px solid var(--color-cork-shadow)',
                                fontWeight: 400
                              }}
                            >
                              {skill}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                  </div>
                </div>
              )}

              {/* Job Description */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
                <h4 style={{ fontSize: 'var(--text-sm)', fontWeight: 750, textTransform: 'uppercase', letterSpacing: '0.04em', color: 'var(--text-secondary)', margin: 0 }}>
                  Description
                </h4>
                <div 
                  style={{ 
                    fontSize: 'var(--text-sm)', 
                    color: 'var(--text)', 
                    lineHeight: 1.6, 
                    whiteSpace: 'pre-wrap',
                    background: 'transparent',
                    padding: 'var(--space-4)',
                    borderRadius: '12px',
                    border: '1px dashed var(--color-cork-shadow)'
                  }}
                >
                  {selectedJob.description}
                </div>
              </div>

              {/* Job Metadata Properties */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-3)', background: 'transparent', padding: 'var(--space-4)', borderRadius: '12px', border: '1px dashed var(--color-cork-shadow)' }}>
                <div>
                  <span style={{ fontSize: '10px', color: 'var(--text-tertiary)', display: 'block' }}>Target Start Date</span>
                  <strong style={{ fontSize: 'var(--text-xs)', color: 'var(--text)' }}>
                    {selectedJob.start_date ? new Date(selectedJob.start_date).toLocaleDateString() : 'Immediate'}
                  </strong>
                </div>
                <div>
                  <span style={{ fontSize: '10px', color: 'var(--text-tertiary)', display: 'block' }}>Status</span>
                  <strong style={{ fontSize: 'var(--text-xs)', color: 'var(--success)' }}>
                    Active / Open
                  </strong>
                </div>
              </div>

            </div>

            {/* Drawer Footer Application Panel */}
            <div 
              style={{ 
                padding: 'var(--space-6)', 
                borderTop: '1px dashed var(--color-cork-shadow)', 
                background: 'transparent',
                display: 'flex',
                flexDirection: 'column',
                gap: 'var(--space-4)'
              }}
            >
              {applySuccess ? (
                <div 
                  style={{ 
                    background: 'var(--success-bg)', 
                    color: 'var(--success)', 
                    padding: 'var(--space-4)', 
                    borderRadius: '10px',
                    border: '1px solid var(--success)',
                    textAlign: 'center'
                  }}
                >
                  <span style={{ fontSize: '24px', display: 'block', marginBottom: '4px' }}>🎉</span>
                  <strong style={{ fontSize: 'var(--text-sm)', display: 'block' }}>Application Submitted!</strong>
                  <p style={{ fontSize: 'var(--text-xs)', color: 'var(--text-secondary)', margin: '4px 0 0' }}>
                    Your application and immutable resume snapshot have been committed.
                  </p>
                </div>
              ) : appliedJobIds.has(selectedJob.id) ? (
                <div 
                  style={{ 
                    background: 'var(--bg-subtle)', 
                    color: 'var(--text-secondary)', 
                    padding: 'var(--space-4)', 
                    borderRadius: '10px',
                    border: '1px solid var(--border)',
                    textAlign: 'center',
                    fontWeight: 600,
                    fontSize: 'var(--text-sm)'
                  }}
                >
                  Applied (Application Committed)
                </div>
              ) : (
                <>
                  {applyError && (
                    <div style={{ background: 'var(--danger-bg)', color: 'var(--danger)', padding: 'var(--space-3)', borderRadius: '8px', fontSize: 'var(--text-xs)', border: '1px solid var(--danger)' }}>
                      <strong>Submission Failed:</strong> {applyError}
                    </div>
                  )}

                  {resumesLoading ? (
                    <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-secondary)', textAlign: 'center' }}>
                      Retrieving resume library...
                    </div>
                  ) : resumes.length === 0 ? (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
                      <div style={{ background: 'var(--warning-bg)', color: 'var(--warning)', padding: 'var(--space-3)', borderRadius: '8px', fontSize: 'var(--text-xs)', border: '1px solid var(--warning)' }}>
                        <strong>No Resumes Found:</strong> You must upload a resume to your library before applying.
                      </div>
                      <Link 
                        to="/candidate/resumes" 
                        className="btn btn--primary" 
                        style={{ borderRadius: '10px', textAlign: 'center', padding: '10px' }}
                      >
                        Go to Resume Library
                      </Link>
                    </div>
                  ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                        <label htmlFor="resume-select" style={{ fontSize: '11px', fontWeight: 700, color: 'var(--text-secondary)' }}>
                          Select Resume to Submit:
                        </label>
                        <select
                          id="resume-select"
                          value={selectedResumeId}
                          onChange={(e) => setSelectedResumeId(e.target.value)}
                          className="form-select"
                          style={{ 
                          padding: '10px 14px', 
                          borderRadius: '0px', 
                          fontSize: '14px', 
                          border: 'none',
                          borderBottom: '1px solid var(--color-warm-cream)',
                          background: 'transparent',
                          color: 'var(--text)',
                          width: '100%'
                        }}
                        >
                          {resumes.map(r => (
                            <option key={r.id} value={r.id}>
                              {r.filename} {r.is_active ? '(Active)' : '(Archived)'}
                            </option>
                          ))}
                        </select>
                        <span style={{ fontSize: '10px', color: 'var(--text-tertiary)', marginTop: '2px' }}>
                          * Active resume is pre-selected by default. Archived resumes remain selectable.
                        </span>
                      </div>

                      {profile && (!profile.email_verified || !profile.phone_verified) ? (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)', marginTop: 'var(--space-2)' }}>
                          <div style={{ background: 'var(--warning-bg)', color: 'var(--warning)', padding: 'var(--space-3)', borderRadius: '8px', fontSize: 'var(--text-xs)', border: '1px solid var(--warning)' }}>
                            <strong>Verification Required:</strong> You must verify your email and phone number in <Link to="/candidate/profile" style={{ color: 'var(--accent)', textDecoration: 'underline', fontWeight: 600 }}>Profile Settings</Link> to apply.
                          </div>
                          <button
                            type="button"
                            className="btn btn--secondary"
                            disabled={true}
                            style={{ 
                              width: '100%', 
                              padding: '12px', 
                              borderRadius: '10px', 
                              fontWeight: 700,
                            }}
                          >
                            Application Locked (Verify Settings)
                          </button>
                        </div>
                      ) : (
                        <button
                          type="button"
                          className="btn btn--primary"
                          onClick={handleApply}
                          disabled={applying}
                          style={{ 
                          width: '100%', 
                          padding: '12px', 
                          borderRadius: '36px', 
                          fontWeight: 500,
                          background: 'var(--color-dark-cork)',
                          color: 'var(--text)',
                          boxShadow: 'none',
                          border: 'none'
                        }}
                        >
                          {applying ? 'Submitting Application...' : 'Submit Application'}
                        </button>
                      )}
                    </div>
                  )}
                </>
              )}
            </div>

          </aside>
        </>
      )}

      {/* Animation pulse utility */}
      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 0.6; }
          50% { opacity: 0.3; }
        }
      `}</style>

    </CandidateLayout>
  )
}
