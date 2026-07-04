import { useState, useEffect, useRef } from 'react'
import { fetchJobRevisions, fetchJobRevisionDetail, type JobRevision, type JobRevisionDetail } from '../../api'

interface RevisionHistoryDrawerProps {
  isOpen: boolean
  onClose: () => void
  jobId: string
  currentValues: {
    title: string
    department: string
    overviewText: string
    responsibilitiesText: string
    requirementsText: string
    workplaceType: string
    employmentType: string
    salaryMin: number | ''
    salaryMax: number | ''
    currency: string
    requiredSkills: string[]
    preferredSkills: string[]
    benefits: string[]
  }
}

export default function RevisionHistoryDrawer({
  isOpen,
  onClose,
  jobId,
  currentValues
}: RevisionHistoryDrawerProps) {
  const [loading, setLoading] = useState(false)
  const [revisions, setRevisions] = useState<JobRevision[]>([])
  const [selectedRevision, setSelectedRevision] = useState<JobRevisionDetail | null>(null)
  const [selectedVersionNum, setSelectedVersionNum] = useState<number | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  const drawerRef = useRef<HTMLDivElement>(null)

  // Escape key close
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose()
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isOpen, onClose])

  // Focus trap
  useEffect(() => {
    if (isOpen && drawerRef.current) {
      const focusable = drawerRef.current.querySelectorAll(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
      )
      if (focusable.length > 0) {
        (focusable[0] as HTMLElement).focus()
      }
    }
  }, [isOpen])

  // Fetch revisions list
  useEffect(() => {
    if (isOpen && jobId) {
      setLoading(true)
      setErrorMessage(null)
      setSelectedRevision(null)
      setSelectedVersionNum(null)
      fetchJobRevisions(jobId)
        .then(data => {
          setRevisions(data)
        })
        .catch(err => {
          setErrorMessage(err.response?.data?.detail || err.message || 'Failed to load revisions.')
        })
        .finally(() => {
          setLoading(false)
        })
    }
  }, [isOpen, jobId])

  const handleSelectRevision = (versionNum: number) => {
    setSelectedVersionNum(versionNum)
    setDetailLoading(true)
    fetchJobRevisionDetail(jobId, versionNum)
      .then(detail => {
        setSelectedRevision(detail)
      })
      .catch(err => {
        alert(err.response?.data?.detail || err.message || 'Failed to load version details.')
      })
      .finally(() => {
        setDetailLoading(false)
      })
  }

  // Helper for parsing raw combined description into sections
  const parseDescriptionSections = (text: string) => {
    const sections = { overview: '', responsibilities: '', requirements: '' }
    if (!text) return sections

    const overviewIndex = text.indexOf('### Role Overview')
    const responsibilitiesIndex = text.indexOf('### Key Responsibilities')
    const requirementsIndex = text.indexOf('### Requirements & Qualifications')

    const indices = [
      { name: 'overview', index: overviewIndex },
      { name: 'responsibilities', index: responsibilitiesIndex },
      { name: 'requirements', index: requirementsIndex }
    ].filter(i => i.index !== -1).sort((a, b) => a.index - b.index)

    for (let i = 0; i < indices.length; i++) {
      const curr = indices[i]
      const next = indices[i + 1]
      const start = curr.index + (curr.name === 'overview' ? 17 : curr.name === 'responsibilities' ? 24 : 33)
      const end = next ? next.index : text.length
      sections[curr.name as 'overview' | 'responsibilities' | 'requirements'] = text.substring(start, end).trim()
    }

    // Fallback if formatting was different
    if (!overviewIndex && !responsibilitiesIndex && !requirementsIndex) {
      sections.overview = text.trim()
    }

    return sections
  }

  if (!isOpen) return null

  // Diff rendering component helper
  const renderFieldComparison = (label: string, oldVal: string, newVal: string) => {
    const isDifferent = oldVal.trim() !== newVal.trim()
    return (
      <div style={{ borderBottom: '1px solid var(--border)', paddingBottom: '16px', marginBottom: '16px' }}>
        <div style={{ fontSize: '11px', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', marginBottom: '8px' }}>
          {label}
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
          {/* Old revision version */}
          <div style={{ 
            padding: '12px', 
            borderRadius: '6px', 
            border: '1px dashed var(--border)',
            backgroundColor: isDifferent ? '#fdf2f2' : 'transparent',
            textDecoration: isDifferent ? 'line-through' : 'none',
            color: isDifferent ? '#9b1c1c' : 'var(--text)',
            fontSize: '13px',
            whiteSpace: 'pre-wrap'
          }}>
            <div style={{ fontSize: '10px', color: 'var(--text-secondary)', marginBottom: '4px' }}>VERSION V{selectedVersionNum}</div>
            {oldVal.trim() || <span style={{ fontStyle: 'italic', color: 'var(--color-ash)' }}>[Empty]</span>}
          </div>

          {/* Current unsaved draft */}
          <div style={{ 
            padding: '12px', 
            borderRadius: '6px', 
            border: '1px solid var(--border)',
            backgroundColor: isDifferent ? '#f3faf4' : 'transparent',
            color: isDifferent ? '#137333' : 'var(--text)',
            fontSize: '13px',
            whiteSpace: 'pre-wrap'
          }}>
            <div style={{ fontSize: '10px', color: 'var(--text-secondary)', marginBottom: '4px' }}>CURRENT DRAFT</div>
            {newVal.trim() || <span style={{ fontStyle: 'italic', color: 'var(--color-ash)' }}>[Empty]</span>}
          </div>
        </div>
      </div>
    )
  }

  const renderListComparison = (label: string, oldList: string[], newList: string[]) => {
    const added = newList.filter(item => !oldList.includes(item))
    const removed = oldList.filter(item => !newList.includes(item))
    const unchanged = oldList.filter(item => newList.includes(item))
    const isDifferent = added.length > 0 || removed.length > 0

    return (
      <div style={{ borderBottom: '1px solid var(--border)', paddingBottom: '16px', marginBottom: '16px' }}>
        <div style={{ fontSize: '11px', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', marginBottom: '8px' }}>
          {label}
        </div>
        {!isDifferent ? (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
            {oldList.map(s => (
              <span key={s} className="badge" style={{ textTransform: 'none' }}>{s}</span>
            ))}
            {oldList.length === 0 && <span style={{ fontStyle: 'italic', fontSize: '13px', color: 'var(--color-ash)' }}>None specified</span>}
          </div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
            {/* Version items */}
            <div style={{ padding: '12px', borderRadius: '6px', border: '1px dashed var(--border)', backgroundColor: '#fdf2f2' }}>
              <div style={{ fontSize: '10px', color: 'var(--text-secondary)', marginBottom: '6px' }}>VERSION V{selectedVersionNum}</div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                {unchanged.map(s => (
                  <span key={s} className="badge" style={{ textTransform: 'none' }}>{s}</span>
                ))}
                {removed.map(s => (
                  <span key={s} className="badge" style={{ textTransform: 'none', backgroundColor: '#fde8e8', color: '#9b1c1c', border: '1px solid #f8b4b4', textDecoration: 'line-through' }}>{s}</span>
                ))}
              </div>
            </div>
            {/* Current items */}
            <div style={{ padding: '12px', borderRadius: '6px', border: '1px solid var(--border)', backgroundColor: '#f3faf4' }}>
              <div style={{ fontSize: '10px', color: 'var(--text-secondary)', marginBottom: '6px' }}>CURRENT DRAFT</div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                {unchanged.map(s => (
                  <span key={s} className="badge" style={{ textTransform: 'none' }}>{s}</span>
                ))}
                {added.map(s => (
                  <span key={s} className="badge" style={{ textTransform: 'none', backgroundColor: '#def7ec', color: '#03543f', border: '1px solid #84e1bc' }}>{s} (added)</span>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    )
  }

  const oldDescParsed = selectedRevision ? parseDescriptionSections(selectedRevision.description) : { overview: '', responsibilities: '', requirements: '' }

  return (
    <div 
      className="drawer-overlay" 
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(23, 25, 28, 0.4)',
        backdropFilter: 'blur(4px)',
        zIndex: 1000,
        display: 'flex',
        justifyContent: 'flex-end',
      }}
      onClick={onClose}
    >
      <div 
        ref={drawerRef}
        className="drawer-content"
        style={{
          width: '100%',
          maxWidth: '850px',
          height: '100%',
          backgroundColor: 'var(--surface)',
          borderLeft: '1px solid var(--border)',
          boxShadow: 'var(--shadow-lg)',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden'
        }}
        onClick={e => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="revision-history-title"
      >
        {/* Header */}
        <div style={{ padding: '24px', borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h3 id="revision-history-title" className="font-signifier" style={{ fontSize: '20px', fontWeight: 600 }}>Revision History Log</h3>
            <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '4px' }}>
              Inspect older versions and compare changes side-by-side
            </p>
          </div>
          <button 
            onClick={onClose} 
            className="icon-btn" 
            style={{ fontSize: '20px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
            aria-label="Close drawer"
          >
            &times;
          </button>
        </div>

        {/* Body Split */}
        <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
          {/* Left panel: versions list */}
          <div style={{ width: '280px', borderRight: '1px solid var(--border)', overflowY: 'auto', backgroundColor: 'var(--bg-subtle)', padding: '16px' }}>
            <h4 style={{ fontSize: '11px', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', marginBottom: '12px' }}>
              Saved Revisions ({revisions.length})
            </h4>

            {loading ? (
              <div style={{ padding: '20px', textAlign: 'center', color: 'var(--text-secondary)' }}>Loading history...</div>
            ) : errorMessage ? (
              <div style={{ padding: '12px', fontSize: '12px', color: '#9b1c1c' }}>{errorMessage}</div>
            ) : revisions.length === 0 ? (
              <div style={{ padding: '20px', textAlign: 'center', fontSize: '13px', color: 'var(--text-secondary)' }}>
                No revisions found. Changes are saved when the status is updated while published.
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {revisions.map(rev => (
                  <button
                    key={rev.id}
                    onClick={() => handleSelectRevision(rev.version)}
                    style={{
                      width: '100%',
                      padding: '12px',
                      borderRadius: '6px',
                      border: '1px solid',
                      borderColor: selectedVersionNum === rev.version ? 'var(--accent)' : 'var(--border)',
                      backgroundColor: selectedVersionNum === rev.version ? 'var(--surface)' : 'transparent',
                      textAlign: 'left',
                      transition: 'all 0.15s ease'
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                      <span style={{ fontWeight: 600, fontSize: '13px' }}>Version V{rev.version}</span>
                      <span className="badge" style={{ fontSize: '9px', padding: '2px 6px' }}>{rev.job_status}</span>
                    </div>
                    <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginBottom: '6px' }}>
                      {new Date(rev.created_at).toLocaleString()}
                    </div>
                    <div style={{ fontSize: '12px', color: 'var(--text)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      💬 {rev.change_reason || 'No details provided'}
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Right panel: comparison display */}
          <div style={{ flex: 1, overflowY: 'auto', padding: '24px', backgroundColor: 'var(--surface)' }}>
            {detailLoading ? (
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '200px' }}>
                <div style={{
                  width: '32px',
                  height: '32px',
                  border: '3px solid var(--border)',
                  borderTopColor: 'var(--accent)',
                  borderRadius: '50%',
                  animation: 'spin 1s linear infinite',
                  marginBottom: '12px'
                }} />
                <span style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>Retrieving revision snapshot...</span>
              </div>
            ) : selectedRevision ? (
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px', paddingBottom: '16px', borderBottom: '2px solid var(--border)' }}>
                  <div>
                    <h4 style={{ fontSize: '16px', fontWeight: 600 }}>Comparing Version V{selectedRevision.version}</h4>
                    <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '4px' }}>
                      Edited by user <strong>{selectedRevision.created_by || 'Recruiter'}</strong> &bull; Reason: {selectedRevision.change_reason || 'N/A'}
                    </p>
                  </div>
                </div>

                {/* Diff Blocks */}
                {renderFieldComparison('Job Title', selectedRevision.title, currentValues.title)}
                {renderFieldComparison('Department', selectedRevision.department, currentValues.department)}
                {renderFieldComparison('Workplace Type', selectedRevision.settings?.workplace_type || 'On-site', currentValues.workplaceType)}
                {renderFieldComparison('Employment Type', selectedRevision.settings?.employment_type || 'Full Time', currentValues.employmentType)}
                
                {renderFieldComparison(
                  'Compensation Min', 
                  selectedRevision.settings?.salary_min !== undefined ? String(selectedRevision.settings.salary_min) : '', 
                  currentValues.salaryMin !== '' ? String(currentValues.salaryMin) : ''
                )}
                {renderFieldComparison(
                  'Compensation Max', 
                  selectedRevision.settings?.salary_max !== undefined ? String(selectedRevision.settings.salary_max) : '', 
                  currentValues.salaryMax !== '' ? String(currentValues.salaryMax) : ''
                )}
                {renderFieldComparison('Currency', selectedRevision.settings?.currency || 'USD', currentValues.currency)}

                {renderFieldComparison('Role Overview', oldDescParsed.overview, currentValues.overviewText)}
                {renderFieldComparison('Key Responsibilities', oldDescParsed.responsibilities, currentValues.responsibilitiesText)}
                {renderFieldComparison('Requirements', oldDescParsed.requirements, currentValues.requirementsText)}

                {renderListComparison('Required Skills', selectedRevision.settings?.required_skills || [], currentValues.requiredSkills)}
                {renderListComparison('Preferred Skills', selectedRevision.settings?.preferred_skills || [], currentValues.preferredSkills)}
                {renderListComparison('Perks & Benefits', selectedRevision.settings?.benefits || [], currentValues.benefits)}

              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', textAlign: 'center', color: 'var(--text-secondary)' }}>
                <div style={{ fontSize: '32px', marginBottom: '12px' }}>🔍</div>
                <h5 style={{ fontWeight: 500, fontSize: '14px', marginBottom: '4px' }}>No Revision Selected</h5>
                <p style={{ fontSize: '12px', maxWidth: '280px' }}>Select a version from the left panel history list to view the differences side-by-side.</p>
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div style={{ padding: '16px 24px', borderTop: '1px solid var(--border)', display: 'flex', justifyContent: 'flex-end', backgroundColor: 'var(--bg-subtle)' }}>
          <button onClick={onClose} className="btn btn--secondary" style={{ border: '1px solid var(--border)' }}>
            Close History
          </button>
        </div>
      </div>
    </div>
  )
}
