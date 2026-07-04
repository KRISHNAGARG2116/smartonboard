import { useState, useEffect, useRef } from 'react'
import { generateJobDescription } from '../../api'

interface AIAssistDrawerProps {
  isOpen: boolean
  onClose: () => void
  jobTitle: string
  department: string
  industry?: string | null
  workplaceType?: string | null
  employmentType?: string | null
  requiredSkills?: string[]
  preferredSkills?: string[]
  onAcceptSection: (section: 'overview' | 'responsibilities' | 'requirements' | 'benefits' | 'qualifications', content: string, mode: 'replace' | 'append') => void
  onAcceptAll: (payload: {
    overview?: string
    responsibilities?: string
    requirements?: string
    benefits?: string
    qualifications?: string
  }) => void
}

const LOADER_STEPS = [
  'Analyzing job specs & department settings...',
  'Generating role overview...',
  'Generating key responsibilities...',
  'Generating requirements & qualifications...',
  'Generating benefits & perks...',
  'Finalizing formatting...'
]

export default function AIAssistDrawer({
  isOpen,
  onClose,
  jobTitle,
  department,
  industry,
  workplaceType,
  employmentType,
  requiredSkills = [],
  preferredSkills = [],
  onAcceptSection,
  onAcceptAll
}: AIAssistDrawerProps) {
  const [loading, setLoading] = useState(false)
  const [loadingStepIdx, setLoadingStepIdx] = useState(0)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  
  // Section locking state
  const [locked, setLocked] = useState({
    overview: false,
    responsibilities: false,
    requirements: false,
    benefits: false,
    qualifications: false
  })

  // Unaccepted AI values
  const [generated, setGenerated] = useState<{
    overview?: string
    responsibilities?: string
    requirements?: string
    benefits?: string
    qualifications?: string
  }>({})

  // Track accepted state for badges (cleared on accept)
  const [unaccepted, setUnaccepted] = useState({
    overview: false,
    responsibilities: false,
    requirements: false,
    benefits: false,
    qualifications: false
  })

  const abortControllerRef = useRef<AbortController | null>(null)
  const loaderIntervalRef = useRef<any>(null)

  // Escape key handler
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
  const drawerRef = useRef<HTMLDivElement>(null)
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

  // Clean up timers & abort controllers
  useEffect(() => {
    return () => {
      if (loaderIntervalRef.current) clearInterval(loaderIntervalRef.current)
      if (abortControllerRef.current) abortControllerRef.current.abort()
    }
  }, [])

  const startLoaderAnimation = () => {
    setLoadingStepIdx(0)
    if (loaderIntervalRef.current) clearInterval(loaderIntervalRef.current)
    loaderIntervalRef.current = setInterval(() => {
      setLoadingStepIdx(prev => (prev < LOADER_STEPS.length - 1 ? prev + 1 : prev))
    }, 3000)
  }

  const stopLoaderAnimation = () => {
    if (loaderIntervalRef.current) {
      clearInterval(loaderIntervalRef.current)
      loaderIntervalRef.current = null
    }
  }

  const handleGenerate = async (targetSection?: 'overview' | 'responsibilities' | 'requirements' | 'benefits' | 'qualifications') => {
    setLoading(true)
    setErrorMessage(null)
    startLoaderAnimation()

    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
    }
    abortControllerRef.current = new AbortController()

    try {
      const sectionParam = targetSection === 'overview' ? 'description' : targetSection
      const res = await generateJobDescription({
        title: jobTitle,
        department,
        industry,
        workplace_type: workplaceType,
        employment_type: employmentType,
        required_skills: requiredSkills,
        preferred_skills: preferredSkills,
        section: sectionParam
      }, {
        signal: abortControllerRef.current.signal,
        idempotencyKey: `idemp-gen-${Date.now()}` // generate a unique attempt key
      })

      if (res.success) {
        if (targetSection) {
          // Targeted regeneration
          setGenerated(prev => ({
            ...prev,
            [targetSection]: res[sectionParam || 'description'] || ''
          }))
          setUnaccepted(prev => ({ ...prev, [targetSection]: true }))
        } else {
          // Full generation
          setGenerated({
            overview: res.description || '',
            responsibilities: res.responsibilities || '',
            requirements: res.requirements || '',
            benefits: res.benefits || '',
            qualifications: res.qualifications || ''
          })
          setUnaccepted({
            overview: !locked.overview,
            responsibilities: !locked.responsibilities,
            requirements: !locked.requirements,
            benefits: !locked.benefits,
            qualifications: !locked.qualifications
          })
        }
      } else {
        setErrorMessage(res.message || 'AI generation returned an error.')
      }
    } catch (err: any) {
      if (err.name === 'CanceledError' || err.name === 'AbortError') {
        console.log('AI generation cancelled.')
      } else {
        setErrorMessage(err.response?.data?.detail || err.message || 'Generation failed.')
      }
    } finally {
      setLoading(false)
      stopLoaderAnimation()
      abortControllerRef.current = null
    }
  }

  const handleCancel = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
      abortControllerRef.current = null
    }
    setLoading(false)
    stopLoaderAnimation()
  }

  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text)
    alert('Copied to clipboard!')
  }

  const toggleLock = (section: 'overview' | 'responsibilities' | 'requirements' | 'benefits' | 'qualifications') => {
    setLocked(prev => ({ ...prev, [section]: !prev[section] }))
  }

  const acceptSection = (section: 'overview' | 'responsibilities' | 'requirements' | 'benefits' | 'qualifications', mode: 'replace' | 'append') => {
    const val = generated[section]
    if (val) {
      onAcceptSection(section, val, mode)
      setUnaccepted(prev => ({ ...prev, [section]: false }))
    }
  }

  const acceptAllGenerated = () => {
    const payload: typeof generated = {}
    if (generated.overview && !locked.overview) payload.overview = generated.overview
    if (generated.responsibilities && !locked.responsibilities) payload.responsibilities = generated.responsibilities
    if (generated.requirements && !locked.requirements) payload.requirements = generated.requirements
    if (generated.benefits && !locked.benefits) payload.benefits = generated.benefits
    if (generated.qualifications && !locked.qualifications) payload.qualifications = generated.qualifications

    onAcceptAll(payload)
    setUnaccepted({
      overview: false,
      responsibilities: false,
      requirements: false,
      benefits: false,
      qualifications: false
    })
    onClose()
  }

  if (!isOpen) return null

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
          maxWidth: '640px',
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
        aria-labelledby="ai-assist-title"
      >
        {/* Header */}
        <div style={{ padding: '24px', borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h3 id="ai-assist-title" className="font-signifier" style={{ fontSize: '20px', fontWeight: 600 }}>AI Authoring Assistant</h3>
            <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '4px' }}>
              Co-write your job description for <strong>{jobTitle || 'Untitled Role'}</strong>
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

        {/* Scrollable Body */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '24px' }}>
          {errorMessage && (
            <div className="badge badge--danger" style={{ width: '100%', padding: '12px', marginBottom: '20px', borderRadius: '4px', textTransform: 'none', display: 'block' }}>
              <strong style={{ display: 'block', marginBottom: '4px' }}>Generation Error</strong>
              {errorMessage}
              <button 
                className="btn btn--sm btn--primary" 
                style={{ marginTop: '8px', display: 'inline-block' }}
                onClick={() => handleGenerate()}
              >
                Retry Request
              </button>
            </div>
          )}

          {loading ? (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '300px', textAlign: 'center' }}>
              <div style={{
                width: '40px',
                height: '40px',
                border: '3px solid var(--border)',
                borderTopColor: 'var(--accent)',
                borderRadius: '50%',
                animation: 'spin 1s linear infinite',
                marginBottom: '20px'
              }} />
              <p style={{ fontWeight: 500, fontSize: '15px' }}>{LOADER_STEPS[loadingStepIdx]}</p>
              <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '6px' }}>This may take up to 20 seconds...</p>
              
              <button 
                onClick={handleCancel}
                className="btn btn--secondary btn--sm" 
                style={{ marginTop: '24px', border: '1px solid var(--border)' }}
              >
                Cancel Generation
              </button>
            </div>
          ) : (
            <>
              {Object.keys(generated).length === 0 ? (
                <div style={{ textAlign: 'center', padding: '40px 20px' }}>
                  <div style={{ fontSize: '40px', marginBottom: '16px' }}>✍️</div>
                  <h4 style={{ fontWeight: 500, fontSize: '16px', marginBottom: '8px' }}>Generate Structured Details</h4>
                  <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '24px', maxWidth: '360px', marginInline: 'auto' }}>
                    Let our AI structure your overview, responsibilities, requirements, and benefits based on the role details.
                  </p>
                  <button 
                    onClick={() => handleGenerate()} 
                    className="btn btn--primary"
                  >
                    Draft Entire Posting
                  </button>
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
                  
                  {/* Overview Section */}
                  <SectionBlock 
                    title="Overview"
                    id="overview"
                    content={generated.overview}
                    isLocked={locked.overview}
                    isUnaccepted={unaccepted.overview}
                    onToggleLock={() => toggleLock('overview')}
                    onRegenerate={() => handleGenerate('overview')}
                    onReplace={() => acceptSection('overview', 'replace')}
                    onAppend={() => acceptSection('overview', 'append')}
                    onCopy={() => handleCopy(generated.overview || '')}
                  />

                  {/* Responsibilities Section */}
                  <SectionBlock 
                    title="Key Responsibilities"
                    id="responsibilities"
                    content={generated.responsibilities}
                    isLocked={locked.responsibilities}
                    isUnaccepted={unaccepted.responsibilities}
                    onToggleLock={() => toggleLock('responsibilities')}
                    onRegenerate={() => handleGenerate('responsibilities')}
                    onReplace={() => acceptSection('responsibilities', 'replace')}
                    onAppend={() => acceptSection('responsibilities', 'append')}
                    onCopy={() => handleCopy(generated.responsibilities || '')}
                  />

                  {/* Requirements Section */}
                  <SectionBlock 
                    title="Requirements"
                    id="requirements"
                    content={generated.requirements}
                    isLocked={locked.requirements}
                    isUnaccepted={unaccepted.requirements}
                    onToggleLock={() => toggleLock('requirements')}
                    onRegenerate={() => handleGenerate('requirements')}
                    onReplace={() => acceptSection('requirements', 'replace')}
                    onAppend={() => acceptSection('requirements', 'append')}
                    onCopy={() => handleCopy(generated.requirements || '')}
                  />

                  {/* Qualifications Section */}
                  <SectionBlock 
                    title="Qualifications"
                    id="qualifications"
                    content={generated.qualifications}
                    isLocked={locked.qualifications}
                    isUnaccepted={unaccepted.qualifications}
                    onToggleLock={() => toggleLock('qualifications')}
                    onRegenerate={() => handleGenerate('qualifications')}
                    onReplace={() => acceptSection('qualifications', 'replace')}
                    onAppend={() => acceptSection('qualifications', 'append')}
                    onCopy={() => handleCopy(generated.qualifications || '')}
                  />

                  {/* Benefits Section */}
                  <SectionBlock 
                    title="Benefits & Perks"
                    id="benefits"
                    content={generated.benefits}
                    isLocked={locked.benefits}
                    isUnaccepted={unaccepted.benefits}
                    onToggleLock={() => toggleLock('benefits')}
                    onRegenerate={() => handleGenerate('benefits')}
                    onReplace={() => acceptSection('benefits', 'replace')}
                    onAppend={() => acceptSection('benefits', 'append')}
                    onCopy={() => handleCopy(generated.benefits || '')}
                  />

                </div>
              )}
            </>
          )}
        </div>

        {/* Footer Actions */}
        <div style={{ padding: '20px 24px', borderTop: '1px solid var(--border)', display: 'flex', justifyContent: 'flex-end', gap: '12px', backgroundColor: 'var(--surface-inset)' }}>
          <button onClick={onClose} className="btn btn--secondary" style={{ border: '1px solid var(--border)' }}>
            Close Drawer
          </button>
          {Object.keys(generated).length > 0 && !loading && (
            <button 
              onClick={acceptAllGenerated} 
              className="btn btn--primary"
            >
              Accept All Changes
            </button>
          )}
        </div>
      </div>

      <style>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  )
}

/* Helper block component */
interface SectionBlockProps {
  title: string
  id: string
  content?: string
  isLocked: boolean
  isUnaccepted: boolean
  onToggleLock: () => void
  onRegenerate: () => void
  onReplace: () => void
  onAppend: () => void
  onCopy: () => void
}

function SectionBlock({
  title,
  content,
  isLocked,
  isUnaccepted,
  onToggleLock,
  onRegenerate,
  onReplace,
  onAppend,
  onCopy
}: SectionBlockProps) {
  if (!content) return null

  return (
    <div style={{ 
      border: '1px solid var(--border)', 
      borderRadius: '8px', 
      padding: '16px',
      backgroundColor: isUnaccepted ? '#f3faf4' : 'transparent',
      borderColor: isUnaccepted ? '#a3d9b1' : 'var(--border)'
    }}>
      {/* Title bar */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <strong style={{ fontSize: '14px', fontWeight: 600 }}>{title}</strong>
          {isUnaccepted && (
            <span style={{ 
              fontSize: '10px', 
              backgroundColor: '#e6f4ea', 
              color: '#137333', 
              padding: '2px 6px', 
              borderRadius: '10px',
              fontWeight: 500
            }}>
              [AI Generated (Unaccepted)]
            </span>
          )}
        </div>

        {/* Utility buttons */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <button 
            onClick={onToggleLock} 
            className="icon-btn" 
            title={isLocked ? 'Unlock section' : 'Lock section'}
            style={{ fontSize: '13px', width: '28px', height: '28px' }}
          >
            {isLocked ? '🔒' : '🔓'}
          </button>
          
          <button 
            onClick={onRegenerate}
            disabled={isLocked}
            className="icon-btn"
            title="Regenerate this section only"
            style={{ fontSize: '13px', width: '28px', height: '28px', opacity: isLocked ? 0.35 : 1 }}
          >
            🔄
          </button>
        </div>
      </div>

      {/* Content display */}
      <div style={{ 
        fontSize: '13px', 
        lineHeight: 1.5, 
        color: 'var(--text)', 
        whiteSpace: 'pre-wrap',
        maxHeight: '180px',
        overflowY: 'auto',
        backgroundColor: 'rgba(255, 255, 255, 0.5)',
        border: '1px solid var(--border)',
        borderRadius: '4px',
        padding: '10px',
        fontFamily: 'monospace'
      }}>
        {content}
      </div>

      {/* Section actions */}
      <div style={{ display: 'flex', gap: '8px', marginTop: '12px', justifyContent: 'flex-end' }}>
        <button 
          onClick={onCopy} 
          className="btn btn--sm btn--secondary" 
          style={{ fontSize: '11px', padding: '4px 8px', border: '1px solid var(--border)' }}
        >
          Copy
        </button>
        <button 
          onClick={onAppend} 
          disabled={isLocked}
          className="btn btn--sm btn--secondary"
          style={{ fontSize: '11px', padding: '4px 8px', border: '1px solid var(--border)', opacity: isLocked ? 0.5 : 1 }}
        >
          Append
        </button>
        <button 
          onClick={onReplace}
          disabled={isLocked}
          className="btn btn--sm btn--primary"
          style={{ fontSize: '11px', padding: '4px 10px', opacity: isLocked ? 0.5 : 1 }}
        >
          Replace Current
        </button>
      </div>
    </div>
  )
}
