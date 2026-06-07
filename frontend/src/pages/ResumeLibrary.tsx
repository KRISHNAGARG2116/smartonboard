import { useState, useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import CandidateLayout from '../components/CandidateLayout'
import { ListRowSkeleton } from '../components/Skeletons'
import EmptyState from '../components/EmptyState'
import {
  fetchCandidateResumes,
  uploadCandidateResume,
  toggleCandidateResumeActive,
  deleteCandidateResume,
  fetchCandidateProfile,
  type CandidateResume
} from '../api'

export default function ResumeLibrary() {
  const [resumes, setResumes] = useState<CandidateResume[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [profile, setProfile] = useState<{ email_verified: boolean; phone_verified: boolean } | null>(null)
  
  // Upload and drag-and-drop state
  const [uploading, setUploading] = useState(false)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [dragActive, setDragActive] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Scanning simulation state
  const [scanningFilename, setScanningFilename] = useState<string | null>(null)

  const loadResumes = async () => {
    try {
      const data = await fetchCandidateResumes()
      setResumes(data)
      setError(null)
      // If the scanning file has appeared in the main resumes list, clear our scanning placeholder
      if (scanningFilename) {
        const found = data.some(r => r.filename === scanningFilename)
        if (found) {
          setScanningFilename(null)
        }
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load resumes. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadResumes()
    fetchCandidateProfile()
      .then(data => {
        if (data && data.profile) {
          setProfile(data.profile)
        }
      })
      .catch(() => {})
  }, [])

  // Poll for resumes updates while a scan is in progress
  useEffect(() => {
    let interval: any
    if (scanningFilename) {
      interval = setInterval(() => {
        loadResumes()
      }, 2000)
    }
    return () => {
      if (interval) clearInterval(interval)
    }
  }, [scanningFilename])

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true)
    } else if (e.type === "dragleave") {
      setDragActive(false)
    }
  }

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)
    setUploadError(null)

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      await processFile(e.dataTransfer.files[0])
    }
  }

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    e.preventDefault()
    setUploadError(null)
    if (e.target.files && e.target.files[0]) {
      await processFile(e.target.files[0])
    }
  }

  const processFile = async (file: File) => {
    // Check verification status
    if (profile && (!profile.email_verified || !profile.phone_verified)) {
      setUploadError("Verification Required: You must verify your email and phone number to upload resumes. Go to Profile Settings to complete verification.")
      return
    }

    // 1. Client-side size validation (5MB)
    const MAX_SIZE = 5 * 1024 * 1024
    if (file.size > MAX_SIZE) {
      setUploadError("File is too large. Maximum size allowed is 5 MB.")
      return
    }

    // 2. Client-side extension validation
    const allowedExtensions = ['.pdf', '.docx', '.txt']
    const fileExt = file.name.slice(file.name.lastIndexOf('.')).toLowerCase()
    if (!allowedExtensions.includes(fileExt)) {
      setUploadError("Invalid file type. Only PDF, DOCX, and TXT files are supported.")
      return
    }

    // Check if limit is reached
    if (resumes.length >= 3) {
      setUploadError("Maximum limit of 3 resumes reached. Please delete an existing resume to upload a new one.")
      return
    }

    setUploading(true)
    setScanningFilename(file.name)

    const formData = new FormData()
    formData.append('file', file)

    try {
      await uploadCandidateResume(formData)
      // Fetch resumes list, start polling
      await loadResumes()
    } catch (err: any) {
      setScanningFilename(null)
      setUploadError(err.response?.data?.detail || 'Failed to upload resume. Please check your internet connection and file content.')
    } finally {
      setUploading(false)
    }
  }

  const handleToggleActive = async (resumeId: string) => {
    setError(null)
    if (profile && (!profile.email_verified || !profile.phone_verified)) {
      setError("Verification Required: You must verify your email and phone number to activate resumes. Go to Profile Settings to complete verification.")
      return
    }
    try {
      await toggleCandidateResumeActive(resumeId)
      await loadResumes()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to activate resume.')
    }
  }

  const handleDelete = async (resumeId: string) => {
    if (!window.confirm("Are you sure you want to permanently delete this resume? This action cannot be undone.")) {
      return
    }
    try {
      await deleteCandidateResume(resumeId)
      await loadResumes()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to delete resume.')
    }
  }

  const triggerFileInput = () => {
    fileInputRef.current?.click()
  }

  return (
    <CandidateLayout>
      <div className="container" style={{ padding: 'var(--space-6) 0 var(--space-12)' }}>
        <div style={{ maxWidth: '800px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: 'var(--space-6)' }}>
          
          {/* Header Card */}
          <div className="card card__body">
            <h3 style={{ fontSize: 'var(--text-lg)', fontWeight: 800, marginBottom: 'var(--space-2)' }}>Resume Library</h3>
            <p style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-sm)', marginBottom: 0 }}>
              Upload and manage your resumes. You can keep up to 3 resumes in your library. 
              The **Active** resume is used to parse your profile details and drive future job matching.
            </p>
          </div>

          {/* Limit Warnings, Verification Check, or Upload Drag and Drop Zone */}
          {resumes.length >= 3 ? (
            <div 
              className="card card__body" 
              style={{ 
                border: '1px dashed var(--color-cork-shadow)', 
                background: 'transparent', 
                display: 'flex', 
                alignItems: 'center', 
                gap: 'var(--space-4)',
                borderRadius: '12px'
              }}
            >
              <span style={{ fontSize: 'var(--text-2xl)' }}>⚠️</span>
              <div>
                <h4 style={{ fontSize: 'var(--text-sm)', fontWeight: 700, color: 'var(--text)', marginBottom: '4px' }}>
                  Maximum Resume Limit Reached
                </h4>
                <p style={{ fontSize: 'var(--text-xs)', color: 'var(--text-secondary)', margin: 0 }}>
                  You have reached the maximum limit of 3 resumes. Please delete one of your existing resumes if you wish to upload a new one.
                </p>
              </div>
            </div>
          ) : profile && (!profile.email_verified || !profile.phone_verified) ? (
            <div 
              className="card card__body" 
              style={{ 
                border: '1px dashed var(--color-cork-shadow)', 
                background: 'transparent', 
                borderRadius: '12px',
                padding: 'var(--space-8) var(--space-6)',
                textAlign: 'center',
              }}
            >
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 'var(--space-3)' }}>
                <div 
                  style={{ 
                    width: '56px', 
                    height: '56px', 
                    borderRadius: '12px', 
                    background: 'transparent', 
                    color: 'var(--text)',
                    display: 'grid',
                    placeItems: 'center',
                    fontSize: '24px',
                    border: '1px dashed var(--color-cork-shadow)'
                  }}
                >
                  🔒
                </div>
                <div>
                  <h4 style={{ fontSize: 'var(--text-base)', fontWeight: 700, marginBottom: '6px' }}>
                    Upload Restricted
                  </h4>
                  <p style={{ fontSize: 'var(--text-xs)', color: 'var(--text-secondary)', margin: 0 }}>
                    Please verify your email and phone number in <Link to="/candidate/profile" style={{ color: 'var(--accent)', textDecoration: 'underline', fontWeight: 600 }}>Profile Settings</Link> to unlock uploads.
                  </p>
                </div>
              </div>
            </div>
          ) : (
            <div 
              className={`card ${dragActive ? 'drag-active' : ''}`}
              style={{
                border: dragActive ? '1px dashed var(--color-warm-cream)' : '1px dashed var(--color-cork-shadow)',
                background: 'transparent',
                borderRadius: '12px',
                padding: 'var(--space-8) var(--space-6)',
                textAlign: 'center',
                cursor: 'pointer',
                transition: 'all var(--duration-normal)',
                position: 'relative'
              }}
              onDragEnter={handleDrag}
              onDragOver={handleDrag}
              onDragLeave={handleDrag}
              onDrop={handleDrop}
              onClick={triggerFileInput}
            >
              <input
                ref={fileInputRef}
                type="file"
                className="file-input-hidden"
                style={{ display: 'none' }}
                accept=".pdf,.docx,.txt"
                onChange={handleFileChange}
                disabled={uploading}
              />
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 'var(--space-3)' }}>
                <div 
                  style={{ 
                    width: '56px', 
                    height: '56px', 
                    borderRadius: '12px', 
                    background: 'transparent', 
                    color: 'var(--text)',
                    display: 'grid',
                    placeItems: 'center',
                    fontSize: '24px',
                    border: '1px dashed var(--color-cork-shadow)'
                  }}
                >
                  📤
                </div>
                <div>
                  <h4 style={{ fontSize: 'var(--text-base)', fontWeight: 700, marginBottom: '6px' }}>
                    {uploading ? 'Uploading and scanning...' : 'Drag & drop your resume here'}
                  </h4>
                  <p style={{ fontSize: 'var(--text-xs)', color: 'var(--text-secondary)', margin: 0 }}>
                    Support for PDF, DOCX, and TXT files up to 5 MB
                  </p>
                </div>
                {!uploading && (
                  <button type="button" className="btn btn--secondary btn--sm" style={{ marginTop: 'var(--space-2)' }}>
                    Browse Files
                  </button>
                )}
              </div>
            </div>
          )}

          {/* Upload Error Banner */}
          {uploadError && (
            <div className="banner banner--danger" style={{ borderRadius: 'var(--radius-sm)', padding: 'var(--space-3) var(--space-4)', fontSize: 'var(--text-xs)' }}>
              ❌ {uploadError}
            </div>
          )}

          {/* General Error Banner */}
          {error && (
            <div className="banner banner--danger" style={{ borderRadius: 'var(--radius-sm)', padding: 'var(--space-3) var(--space-4)', fontSize: 'var(--text-xs)' }}>
              ❌ {error}
            </div>
          )}

          {/* Resume List Card */}
          <div className="card">
            <div className="card__header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h3 style={{ fontSize: 'var(--text-sm)', fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                Your Resumes ({resumes.length}/3)
              </h3>
            </div>
            
            <div className="card__body" style={{ padding: 0 }}>
              {loading ? (
                <div style={{ padding: 'var(--space-6)', display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
                  <ListRowSkeleton />
                  <ListRowSkeleton />
                </div>
              ) : resumes.length === 0 && !scanningFilename ? (
                <div style={{ padding: 'var(--space-6)' }}>
                  <EmptyState
                    type="resumes"
                    title="No Resumes Uploaded"
                    description="Upload your first resume above. SmartOnboard parses and hashes it as a trusted signal for hiring."
                  />
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column' }}>
                  {/* Scanning Placeholder */}
                  {scanningFilename && (
                    <div 
                      style={{ 
                        padding: 'var(--space-4) var(--space-6)', 
                        borderBottom: '1px dashed var(--color-cork-shadow)',
                        background: 'transparent',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between'
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-4)' }}>
                        <div className="spinner" style={{ width: '18px', height: '18px', border: '2px solid var(--accent)', borderTopColor: 'transparent', borderRadius: '50%' }} />
                        <div>
                          <h4 style={{ fontSize: 'var(--text-sm)', fontWeight: 700, margin: 0 }}>{scanningFilename}</h4>
                          <p style={{ fontSize: '11px', color: 'var(--text-secondary)', margin: '2px 0 0 0' }}>
                            Scanning for malware and parsing details...
                          </p>
                        </div>
                      </div>
                      <span className="badge badge--interview">Processing</span>
                    </div>
                  )}

                  {/* Resumes List */}
                  {resumes.map((resume, idx) => (
                    <ResumeItem 
                      key={resume.id}
                      resume={resume}
                      onSetActive={handleToggleActive}
                      onDelete={handleDelete}
                      isLast={idx === resumes.length - 1}
                    />
                  ))}
                </div>
              )}
            </div>
          </div>

        </div>
      </div>

      <style>{`
        .spinner {
          animation: spin 800ms linear infinite;
        }
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
        .file-input-hidden {
          position: absolute;
          inset: 0;
          opacity: 0;
          cursor: pointer;
        }
        .drag-active {
          box-shadow: none;
        }
      `}</style>
    </CandidateLayout>
  )
}

interface ResumeItemProps {
  resume: CandidateResume
  onSetActive: (id: string) => void
  onDelete: (id: string) => void
  isLast: boolean
}

function ResumeItem({ resume, onSetActive, onDelete, isLast }: ResumeItemProps) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div 
      style={{ 
        padding: 'var(--space-5) var(--space-6)', 
        borderBottom: isLast ? 'none' : '1px dashed var(--color-cork-shadow)',
        display: 'flex',
        flexDirection: 'column',
        gap: 'var(--space-3)',
        transition: 'background var(--duration-fast) var(--ease-out)'
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-4)', justifyContent: 'space-between' }}>
        
        {/* Name and Meta */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-4)' }}>
          <span style={{ fontSize: '24px' }}>📄</span>
          <div>
            <h4 style={{ fontSize: '14px', fontWeight: 500, margin: 0, display: 'flex', alignItems: 'center', gap: 'var(--space-2)', color: 'var(--text)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {resume.filename}
              {resume.is_active && <span className="badge badge--hire">Active</span>}
            </h4>
            <p style={{ fontSize: '11px', color: 'var(--text-secondary)', margin: '4px 0 0 0' }}>
              Uploaded on {new Date(resume.created_at).toLocaleDateString(undefined, { dateStyle: 'medium' })}
            </p>
          </div>
        </div>

        {/* Action Buttons */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
          {/* Collapse/Expand details */}
          <button 
            type="button" 
            className="btn btn--ghost btn--sm" 
            onClick={() => setExpanded(!expanded)}
            style={{ paddingInline: '8px' }}
          >
            {expanded ? 'Hide Info' : 'Show Info'}
          </button>

          {!resume.is_active && (
            <button 
              type="button" 
              className="btn btn--secondary btn--sm" 
              onClick={() => onSetActive(resume.id)}
            >
              Set Active
            </button>
          )}

          <button 
            type="button" 
            className="btn btn--ghost btn--sm" 
            onClick={() => onDelete(resume.id)}
            style={{ color: 'var(--text)' }}
          >
            Delete
          </button>
        </div>

      </div>

      {/* Expanded details (extracted skills & summary) */}
      {expanded && (
        <div 
          style={{ 
            background: 'transparent', 
            padding: 'var(--space-4) var(--space-5)', 
            borderRadius: '12px',
            fontSize: 'var(--text-xs)',
            display: 'flex',
            flexDirection: 'column',
            gap: 'var(--space-3)',
            marginTop: '4px',
            border: '1px dashed var(--color-cork-shadow)'
          }}
        >
          {/* Summary Section */}
          <div>
            <span style={{ fontWeight: 700, color: 'var(--text)', display: 'block', marginBottom: '4px' }}>Summary</span>
            <p style={{ color: 'var(--text-secondary)', margin: 0, lineHeight: 'var(--leading-relaxed)' }}>
              {resume.parsed_summary || 'No summary extracted yet.'}
            </p>
          </div>

          {/* Skills Section */}
          <div>
            <span style={{ fontWeight: 700, color: 'var(--text)', display: 'block', marginBottom: '6px' }}>Extracted Skills</span>
            {resume.parsed_skills && resume.parsed_skills.length > 0 ? (
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                {resume.parsed_skills.map(skill => (
                  <span 
                    key={skill} 
                    style={{ 
                      background: 'transparent', 
                      border: '1px solid var(--color-cork-shadow)',
                      padding: '3px 8px',
                      borderRadius: '6px',
                      color: 'var(--text)',
                      fontWeight: 500,
                      fontSize: '10px'
                    }}
                  >
                    {skill}
                  </span>
                ))}
              </div>
            ) : (
              <p style={{ color: 'var(--text-secondary)', margin: 0 }}>No skills extracted yet.</p>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
