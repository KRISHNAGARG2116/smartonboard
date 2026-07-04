import { useState, useEffect, useCallback, useRef, lazy, Suspense } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import AppLayout from '../../components/AppLayout'
import { useAuth } from '../../context/AuthContext'
import { 
  fetchJob, 
  createJob, 
  updateJob, 
  fetchCompanyUsers,
  fetchCompany,
  suggestSkills,
  type User
} from '../../api'
import SteepCard from '../../components/design-system/SteepCard'
import SteepButton from '../../components/design-system/SteepButton'
import SteepInput from '../../components/design-system/SteepInput'
import SteepBadge from '../../components/design-system/SteepBadge'

// Reusable Preview Subcomponents
import JobPreviewHeader from '../../components/job-preview/JobPreviewHeader'
import JobPreviewFitRing from '../../components/job-preview/JobPreviewFitRing'
import JobPreviewSkills from '../../components/job-preview/JobPreviewSkills'
import JobPreviewDescription, { combineDescription, parseDescription } from '../../components/job-preview/JobPreviewDescription'
import JobPreviewMetadata from '../../components/job-preview/JobPreviewMetadata'

// Lazy-loaded AI and Revision history compare components
const AIAssistDrawer = lazy(() => import('./AIAssistDrawer'))
const RevisionHistoryDrawer = lazy(() => import('./RevisionHistoryDrawer'))

export default function RecruiterJobBuilder() {
  const { id } = useParams<{ id?: string }>()
  const navigate = useNavigate()
  const { user } = useAuth()

  // Component states
  const [loading, setLoading] = useState(true)
  const [activeStep, setActiveStep] = useState(1)
  const [companyUsers, setCompanyUsers] = useState<User[]>([])
  const [companyName, setCompanyName] = useState('Our Company')
  
  // Autosave & Concurrency states
  const [editingJobId, setEditingJobId] = useState<string | null>(id || null)
  const [jobUpdatedAt, setJobUpdatedAt] = useState<string | null>(null)
  const [saveState, setSaveState] = useState<'saved' | 'saving' | 'unsaved' | 'failed' | 'offline'>('saved')
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false)
  const [isOnline, setIsOnline] = useState(navigator.onLine)

  // SPA navigation guard states
  const [showNavBlockerModal, setShowNavBlockerModal] = useState(false)
  const [pendingNavigationPath, setPendingNavigationPath] = useState<string | number | null>(null)

  // Concurrency conflict (409) modal states
  const [showConflictModal, setShowConflictModal] = useState(false)
  const [conflictErrorMessage, setConflictErrorMessage] = useState('')
  const [showConfirmForceModal, setShowConfirmForceModal] = useState(false)

  // Mobile validation drawer state
  const [isMobileValidationOpen, setIsMobileValidationOpen] = useState(false)

  // Phase B.2 Drawer states
  const [isAIAssistOpen, setIsAIAssistOpen] = useState(false)
  const [isHistoryOpen, setIsHistoryOpen] = useState(false)
  const [isPublishing, setIsPublishing] = useState(false)

  // AI Unaccepted & Lock statuses
  const [isAIUnaccepted, setIsAIUnaccepted] = useState({
    overview: false,
    responsibilities: false,
    requirements: false
  })
  const [isLocked, setIsLocked] = useState({
    overview: false,
    responsibilities: false,
    requirements: false
  })

  // Skill Suggestions & Cache
  const [skillSuggestions, setSkillSuggestions] = useState<string[]>([])
  const [suggestionsLoading, setSuggestionsLoading] = useState(false)
  const skillSuggestionsCacheRef = useRef<Record<string, any>>({})

  // Form Fields
  // Step 1: Basics
  const [title, setTitle] = useState('')
  const [department, setDepartment] = useState('Engineering')
  const [employmentType, setEmploymentType] = useState('Full Time')
  const [workplaceType, setWorkplaceType] = useState('On-site')
  const [officeAddress, setOfficeAddress] = useState('')
  const [openings, setOpenings] = useState(1)

  // Step 2: Description (Split locally, combined on save)
  const [overviewText, setOverviewText] = useState('')
  const [responsibilitiesText, setResponsibilitiesText] = useState('')
  const [requirementsText, setRequirementsText] = useState('')

  // Step 3: Skills
  const [requiredSkills, setRequiredSkills] = useState<string[]>([])
  const [preferredSkills, setPreferredSkills] = useState<string[]>([])
  const [languages, setLanguages] = useState<string[]>([])

  // Skill input helper text fields
  const [reqSkillInput, setReqSkillInput] = useState('')
  const [prefSkillInput, setPrefSkillInput] = useState('')
  const [langInput, setLangInput] = useState('')

  // Step 4: Compensation
  const [salaryMin, setSalaryMin] = useState<number | ''>('')
  const [salaryMax, setSalaryMax] = useState<number | ''>('')
  const [currency, setCurrency] = useState('USD')
  const [hideSalary, setHideSalary] = useState(false)
  const [benefits, setBenefits] = useState<string[]>([])
  const [benefitInput, setBenefitInput] = useState('')

  // Step 5: Hiring Team
  const [hiringManagerId, setHiringManagerId] = useState<string>('')
  const [recruiterIds, setRecruiterIds] = useState<string[]>([])
  const [interviewerIds, setInterviewerIds] = useState<string[]>([])

  // Step 7: Final status
  const [jobStatus, setJobStatus] = useState<'draft' | 'open' | 'closed'>('draft')

  // Refs for tracking changes and timers
  const autosaveTimerRef = useRef<any>(null)
  const isSavingRef = useRef(false)
  const lastSavedStateRef = useRef<string>('')

  // Track network status
  useEffect(() => {
    const goOnline = () => setIsOnline(true)
    const goOffline = () => {
      setIsOnline(false)
      setSaveState('offline')
    }
    window.addEventListener('online', goOnline)
    window.addEventListener('offline', goOffline)
    return () => {
      window.removeEventListener('online', goOnline)
      window.removeEventListener('offline', goOffline)
    }
  }, [])

  // Form value string snapshot for change detection
  const getFormStateString = useCallback(() => {
    return JSON.stringify({
      title, department, employmentType, workplaceType, officeAddress, openings,
      overviewText, responsibilitiesText, requirementsText,
      requiredSkills, preferredSkills, languages,
      salaryMin, salaryMax, currency, hideSalary, benefits,
      hiringManagerId, recruiterIds, interviewerIds, jobStatus
    })
  }, [
    title, department, employmentType, workplaceType, officeAddress, openings,
    overviewText, responsibilitiesText, requirementsText,
    requiredSkills, preferredSkills, languages,
    salaryMin, salaryMax, currency, hideSalary, benefits,
    hiringManagerId, recruiterIds, interviewerIds, jobStatus
  ])

  // Initial load
  useEffect(() => {
    async function init() {
      setLoading(true)
      try {
        const [users, co] = await Promise.all([
          fetchCompanyUsers(),
          fetchCompany().catch(() => null)
        ])
        setCompanyUsers(users)
        if (co) {
          setCompanyName(co.name)
        }

        // Determine if we restore from pointer or edit route
        let loadedJob: any = null
        let restoreStep = 1

        const localPointerRaw = localStorage.getItem('smartonboard_job_builder_pointer')
        const pointer = localPointerRaw ? JSON.parse(localPointerRaw) : null

        if (id) {
          // Editing existing job
          loadedJob = await fetchJob(id)
          // Tenant isolation check
          if (loadedJob.company_id !== user?.company_id) {
            alert('Access Denied: You do not have permissions to edit this job posting.')
            navigate('/recruiter/jobs')
            return
          }
          if (pointer && pointer.jobId === id) {
            restoreStep = pointer.currentStep || 1
          }
        } else if (pointer && pointer.jobId) {
          // Recovering draft
          try {
            const draftJob = await fetchJob(pointer.jobId)
            if (draftJob && draftJob.status === 'draft' && draftJob.company_id === user?.company_id) {
              loadedJob = draftJob
              restoreStep = pointer.currentStep || 1
              setEditingJobId(pointer.jobId)
              console.log('Restored draft edit session from pointer.')
            }
          } catch {
            localStorage.removeItem('smartonboard_job_builder_pointer')
          }
        }

        if (loadedJob) {
          setTitle(loadedJob.title || '')
          setDepartment(loadedJob.department || 'Engineering')
          setJobStatus(loadedJob.status || 'draft')
          setJobUpdatedAt(loadedJob.updated_at)

          const s = loadedJob.settings || {}
          setEmploymentType(s.employment_type || 'Full Time')
          setWorkplaceType(s.workplace_type || 'On-site')
          setOfficeAddress(s.office_address || '')
          setOpenings(s.openings ?? 1)

          // Parse combined description
          const parsed = parseDescription(loadedJob.description || '')
          setOverviewText(parsed.overview || '')
          setResponsibilitiesText(parsed.responsibilities || '')
          setRequirementsText(parsed.requirements || '')

          setRequiredSkills(s.required_skills || [])
          setPreferredSkills(s.preferred_skills || [])
          setLanguages(s.languages || [])

          setSalaryMin(s.salary_min ?? '')
          setSalaryMax(s.salary_max ?? '')
          setCurrency(s.currency || 'USD')
          setHideSalary(s.hide_salary || false)
          setBenefits(s.benefits || [])

          setHiringManagerId(s.hiring_manager_id || '')
          setRecruiterIds(s.recruiter_ids || [])
          setInterviewerIds(s.interviewer_ids || [])

          setActiveStep(restoreStep)
        }
      } catch (err) {
        console.error('Failed to load builder context:', err)
      } finally {
        setLoading(false)
        // Set last saved snapshot
        setTimeout(() => {
          lastSavedStateRef.current = getFormStateString()
          setHasUnsavedChanges(false)
        }, 100)
      }
    }
    init()
  }, [id, user, navigate, getFormStateString])

  // Core Save function
  const handleAutosave = useCallback(async (forcedStatus?: 'draft' | 'open' | 'closed', forceOverwriteTimestamp?: string) => {
    if (!isOnline) {
      setSaveState('offline')
      return false
    }
    if (isSavingRef.current) return false

    const combinedDesc = combineDescription(overviewText, responsibilitiesText, requirementsText)
    const payload = {
      title: title || 'Untitled Draft Job',
      department,
      description: combinedDesc,
      status: forcedStatus || jobStatus,
      settings: {
        workplace_type: workplaceType,
        office_address: officeAddress,
        employment_type: employmentType,
        openings: openings ? parseInt(openings as any, 10) : 1,
        salary_min: salaryMin !== '' ? parseFloat(salaryMin as any) : null,
        salary_max: salaryMax !== '' ? parseFloat(salaryMax as any) : null,
        currency,
        hide_salary: hideSalary,
        benefits,
        required_skills: requiredSkills,
        preferred_skills: preferredSkills,
        languages,
        hiring_manager_id: hiringManagerId || null,
        recruiter_ids: recruiterIds,
        interviewer_ids: interviewerIds
      },
      client_updated_at: forceOverwriteTimestamp || jobUpdatedAt || undefined
    }

    isSavingRef.current = true
    setSaveState('saving')

    try {
      if (editingJobId) {
        // Update
        const updated = await updateJob(editingJobId, payload)
        setJobUpdatedAt(updated.updated_at)
        setJobStatus(updated.status as 'draft' | 'open' | 'closed')
      } else {
        // Create
        const created = await createJob(payload)
        setEditingJobId(created.id)
        setJobUpdatedAt(created.updated_at)
        setJobStatus(created.status as 'draft' | 'open' | 'closed')
        // Push state to url quietly
        window.history.replaceState(null, '', `/recruiter/jobs/${created.id}/edit`)
      }
      
      // Update saved reference snapshot
      lastSavedStateRef.current = getFormStateString()
      setHasUnsavedChanges(false)
      setSaveState('saved')
      isSavingRef.current = false
      return true
    } catch (err: any) {
      isSavingRef.current = false
      if (err.response?.status === 409) {
        setSaveState('failed')
        setConflictErrorMessage(err.response?.data?.detail || 'Another recruiter modified this job details.')
        setShowConflictModal(true)
      } else {
        setSaveState('failed')
      }
      return false
    }
  }, [
    editingJobId, jobUpdatedAt, isOnline, title, department, employmentType, workplaceType, officeAddress, openings,
    overviewText, responsibilitiesText, requirementsText, requiredSkills, preferredSkills, languages,
    salaryMin, salaryMax, currency, hideSalary, benefits, hiringManagerId, recruiterIds, interviewerIds, jobStatus, getFormStateString
  ])

  // Listen for local changes to trigger hasUnsavedChanges and debounced autosave
  useEffect(() => {
    if (loading) return
    const currentSnap = getFormStateString()
    if (currentSnap !== lastSavedStateRef.current) {
      setHasUnsavedChanges(true)
      setSaveState('unsaved')

      // Debounce autosave 20s
      if (autosaveTimerRef.current) clearTimeout(autosaveTimerRef.current)
      autosaveTimerRef.current = setTimeout(() => {
        handleAutosave()
      }, 20000)
    } else {
      setHasUnsavedChanges(false)
      setSaveState('saved')
    }

    return () => {
      if (autosaveTimerRef.current) clearTimeout(autosaveTimerRef.current)
    }
  }, [getFormStateString, loading, handleAutosave])

  // Save local recovery pointer
  useEffect(() => {
    if (editingJobId) {
      localStorage.setItem(
        'smartonboard_job_builder_pointer',
        JSON.stringify({
          jobId: editingJobId,
          updatedAt: jobUpdatedAt || new Date().toISOString(),
          currentStep: activeStep,
          hasUnsavedChanges
        })
      )
    } else {
      localStorage.removeItem('smartonboard_job_builder_pointer')
    }
  }, [editingJobId, jobUpdatedAt, activeStep, hasUnsavedChanges])

  // SPA navigation interceptor
  useEffect(() => {
    if (!hasUnsavedChanges) return

    const handleAnchorClick = (e: MouseEvent) => {
      const target = e.target as HTMLElement
      const anchor = target.closest('a')
      if (anchor) {
        const href = anchor.getAttribute('href')
        // Exclude in-page fragments
        if (href && !href.startsWith('#') && !href.startsWith('javascript:')) {
          e.preventDefault()
          e.stopPropagation()
          setPendingNavigationPath(href)
          setShowNavBlockerModal(true)
        }
      }
    }

    document.addEventListener('click', handleAnchorClick, true)
    return () => {
      document.removeEventListener('click', handleAnchorClick, true)
    }
  }, [hasUnsavedChanges])

  // Popstate / Back button interceptor
  useEffect(() => {
    if (!hasUnsavedChanges) return

    const handlePopState = () => {
      window.history.pushState(null, '', window.location.href)
      setPendingNavigationPath(-1) // special indication for goBack
      setShowNavBlockerModal(true)
    }

    window.history.pushState(null, '', window.location.href)
    window.addEventListener('popstate', handlePopState)
    return () => {
      window.removeEventListener('popstate', handlePopState)
    }
  }, [hasUnsavedChanges])

  // beforeunload handler
  useEffect(() => {
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      if (hasUnsavedChanges) {
        e.preventDefault()
        e.returnValue = 'You have unsaved changes. Are you sure you want to leave?'
        return e.returnValue
      }
    }
    window.addEventListener('beforeunload', handleBeforeUnload)
    return () => window.removeEventListener('beforeunload', handleBeforeUnload)
  }, [hasUnsavedChanges])

  // Contextual Skill suggestions debounced + cached
  useEffect(() => {
    if (!title.trim()) {
      setSkillSuggestions([])
      return
    }

    const cacheKey = `${title.toLowerCase().trim()}:${department.toLowerCase().trim()}`
    if (skillSuggestionsCacheRef.current[cacheKey]) {
      const cached = skillSuggestionsCacheRef.current[cacheKey]
      const allSuggested = Array.from(new Set([
        ...cached.required_skills,
        ...cached.preferred_skills,
        ...cached.technologies,
        ...cached.languages
      ]))
      setSkillSuggestions(allSuggested)
      return
    }

    setSuggestionsLoading(true)
    const handler = setTimeout(() => {
      suggestSkills({
        title,
        department,
        existing_skills: [...requiredSkills, ...preferredSkills]
      })
        .then(res => {
          skillSuggestionsCacheRef.current[cacheKey] = res
          const allSuggested = Array.from(new Set([
            ...res.required_skills,
            ...res.preferred_skills,
            ...res.technologies,
            ...res.languages
          ]))
          setSkillSuggestions(allSuggested)
        })
        .catch(err => console.error('Failed to get skill suggestions:', err))
        .finally(() => setSuggestionsLoading(false))
    }, 800)

    return () => clearTimeout(handler)
  }, [title, department])

  const refreshSkillSuggestions = () => {
    if (!title.trim()) return
    const cacheKey = `${title.toLowerCase().trim()}:${department.toLowerCase().trim()}`
    delete skillSuggestionsCacheRef.current[cacheKey]
    setSuggestionsLoading(true)
    suggestSkills({
      title,
      department,
      existing_skills: [...requiredSkills, ...preferredSkills]
    })
      .then(res => {
        skillSuggestionsCacheRef.current[cacheKey] = res
        const allSuggested = Array.from(new Set([
          ...res.required_skills,
          ...res.preferred_skills,
          ...res.technologies,
          ...res.languages
        ]))
        setSkillSuggestions(allSuggested)
      })
      .catch(err => console.error('Failed to refresh skill suggestions:', err))
      .finally(() => setSuggestionsLoading(false))
  }

  // Keyboard Shortcuts Handler
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Ctrl/Cmd + S -> Save Draft
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 's') {
        e.preventDefault()
        handleAutosave()
      }
      // Ctrl/Cmd + Enter -> Publish (Only on final step)
      if ((e.ctrlKey || e.metaKey) && e.key === 'Enter' && activeStep === 7) {
        e.preventDefault()
        handlePublish()
      }
      // Esc -> Close Modals
      if (e.key === 'Escape') {
        setShowConflictModal(false)
        setShowNavBlockerModal(false)
        setShowConfirmForceModal(false)
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [handleAutosave, activeStep])

  // Handle SPA block confirmation choices
  const confirmNavigation = async (action: 'save' | 'discard' | 'cancel') => {
    setShowNavBlockerModal(false)
    if (action === 'cancel') {
      setPendingNavigationPath(null)
      return
    }

    if (action === 'save') {
      const saved = await handleAutosave()
      if (!saved) return // Keep them here if save failed (e.g. 409 conflict)
    }

    // Discard unsaved state to bypass protection
    lastSavedStateRef.current = getFormStateString()
    setHasUnsavedChanges(false)

    // Execute navigation
    if (pendingNavigationPath === -1) {
      navigate(-2) // Account for pushState entry offset
    } else if (typeof pendingNavigationPath === 'string') {
      navigate(pendingNavigationPath)
    }
    setPendingNavigationPath(null)
  }

  // Handle 409 Conflict resolutions
  const handleReloadLatest = async () => {
    setShowConflictModal(false)
    setLoading(true)
    try {
      if (editingJobId) {
        const loadedJob = await fetchJob(editingJobId)
        setTitle(loadedJob.title || '')
        setDepartment(loadedJob.department || 'Engineering')
        setJobStatus(loadedJob.status || 'draft')
        setJobUpdatedAt(loadedJob.updated_at)

        const s = loadedJob.settings || {}
        setEmploymentType(s.employment_type || 'Full Time')
        setWorkplaceType(s.workplace_type || 'On-site')
        setOfficeAddress(s.office_address || '')
        setOpenings(s.openings ?? 1)

        const parsed = parseDescription(loadedJob.description || '')
        setOverviewText(parsed.overview || '')
        setResponsibilitiesText(parsed.responsibilities || '')
        setRequirementsText(parsed.requirements || '')

        setRequiredSkills(s.required_skills || [])
        setPreferredSkills(s.preferred_skills || [])
        setLanguages(s.languages || [])

        setSalaryMin(s.salary_min ?? '')
        setSalaryMax(s.salary_max ?? '')
        setCurrency(s.currency || 'USD')
        setHideSalary(s.hide_salary || false)
        setBenefits(s.benefits || [])

        setHiringManagerId(s.hiring_manager_id || '')
        setRecruiterIds(s.recruiter_ids || [])
        setInterviewerIds(s.interviewer_ids || [])
      }
    } catch {
      alert('Error reloading latest job details from server.')
    } finally {
      setLoading(false)
      setTimeout(() => {
        lastSavedStateRef.current = getFormStateString()
        setHasUnsavedChanges(false)
      }, 100)
    }
  }

  const handleForceOverwriteSubmit = async () => {
    setShowConfirmForceModal(false)
    setShowConflictModal(false)
    if (editingJobId) {
      try {
        // Fetch server's current timestamp
        const latest = await fetchJob(editingJobId)
        const success = await handleAutosave(undefined, latest.updated_at)
        if (success) {
          alert('Force overwrite succeeded.')
        }
      } catch {
        alert('Force overwrite failed.')
      }
    }
  }

  // Skills & tags adding helpers
  const addTag = (type: 'req' | 'pref' | 'lang' | 'benefit') => {
    if (type === 'req') {
      const val = reqSkillInput.trim()
      if (val && !requiredSkills.includes(val)) {
        setRequiredSkills([...requiredSkills, val])
      }
      setReqSkillInput('')
    } else if (type === 'pref') {
      const val = prefSkillInput.trim()
      if (val && !preferredSkills.includes(val)) {
        setPreferredSkills([...preferredSkills, val])
      }
      setPrefSkillInput('')
    } else if (type === 'lang') {
      const val = langInput.trim()
      if (val && !languages.includes(val)) {
        setLanguages([...languages, val])
      }
      setLangInput('')
    } else if (type === 'benefit') {
      const val = benefitInput.trim()
      if (val && !benefits.includes(val)) {
        setBenefits([...benefits, val])
      }
      setBenefitInput('')
    }
  }

  const removeTag = (type: 'req' | 'pref' | 'lang' | 'benefit', item: string) => {
    if (type === 'req') {
      setRequiredSkills(requiredSkills.filter(s => s !== item))
    } else if (type === 'pref') {
      setPreferredSkills(preferredSkills.filter(s => s !== item))
    } else if (type === 'lang') {
      setLanguages(languages.filter(s => s !== item))
    } else if (type === 'benefit') {
      setBenefits(benefits.filter(s => s !== item))
    }
  }

  // AI acceptance handlers
  const handleAcceptAISection = (
    section: 'overview' | 'responsibilities' | 'requirements' | 'benefits' | 'qualifications',
    content: string,
    mode: 'replace' | 'append'
  ) => {
    if (section === 'overview') {
      if (isLocked.overview) return
      setOverviewText(prev => mode === 'replace' ? content : `${prev}\n\n${content}`)
      setIsAIUnaccepted(p => ({ ...p, overview: true }))
    } else if (section === 'responsibilities') {
      if (isLocked.responsibilities) return
      setResponsibilitiesText(prev => mode === 'replace' ? content : `${prev}\n\n${content}`)
      setIsAIUnaccepted(p => ({ ...p, responsibilities: true }))
    } else if (section === 'requirements') {
      if (isLocked.requirements) return
      setRequirementsText(prev => mode === 'replace' ? content : `${prev}\n\n${content}`)
      setIsAIUnaccepted(p => ({ ...p, requirements: true }))
    } else if (section === 'qualifications') {
      if (isLocked.requirements) return
      setRequirementsText(prev => `${prev}\n\n### Qualifications\n${content}`)
      setIsAIUnaccepted(p => ({ ...p, requirements: true }))
    } else if (section === 'benefits') {
      const list = parseBulletsToList(content)
      if (mode === 'replace') {
        setBenefits(list)
      } else {
        const combined = Array.from(new Set([...benefits, ...list]))
        setBenefits(combined)
      }
    }
  }

  const handleAcceptAllAI = (payload: {
    overview?: string
    responsibilities?: string
    requirements?: string
    benefits?: string
    qualifications?: string
  }) => {
    if (payload.overview && !isLocked.overview) {
      setOverviewText(payload.overview)
      setIsAIUnaccepted(p => ({ ...p, overview: true }))
    }
    if (payload.responsibilities && !isLocked.responsibilities) {
      setResponsibilitiesText(payload.responsibilities)
      setIsAIUnaccepted(p => ({ ...p, responsibilities: true }))
    }
    if (payload.requirements && !isLocked.requirements) {
      setRequirementsText(payload.requirements)
      setIsAIUnaccepted(p => ({ ...p, requirements: true }))
    }
    if (payload.qualifications && !isLocked.requirements) {
      setRequirementsText(prev => `${prev}\n\n### Qualifications\n${payload.qualifications}`)
      setIsAIUnaccepted(p => ({ ...p, requirements: true }))
    }
    if (payload.benefits) {
      const list = parseBulletsToList(payload.benefits)
      setBenefits(list)
    }
  }

  const parseBulletsToList = (text: string) => {
    if (!text) return []
    return text
      .split(/\r?\n/)
      .map(line => line.replace(/^[\s\-\*\u2022\d\.\)]+/, '').trim())
      .filter(line => line.length > 0)
  }

  const formatSalary = (val: number | string | undefined | null, curr: string) => {
    if (val === undefined || val === null || val === '') return ''
    const num = Number(val)
    if (isNaN(num)) return ''
    if (curr === 'INR') {
      if (num >= 100000) {
        return `₹${(num / 100000).toFixed(1)}L`
      }
      return `₹${num.toLocaleString('en-IN')}`
    }
    const symbol = curr === 'USD' ? '$' : curr === 'EUR' ? '€' : curr === 'GBP' ? '£' : `${curr} `
    if (num >= 1000) {
      return `${symbol}${(num / 1000).toFixed(0)}k`
    }
    return `${symbol}${num.toLocaleString()}`
  }

  // Stepper handlers
  const navigateToStep = async (stepNum: number) => {
    if (stepNum === activeStep) return
    // Validate Step 1 before leaving it
    if (activeStep === 1 && stepNum > 1) {
      if (!title.trim()) return
    }

    // Save changes immediately on step changes
    await handleAutosave()
    setActiveStep(stepNum)
  }

  // Real-time Validation Checks & Quality Analyzer
  const getValidationReport = () => {
    const blockers: { id: string; label: string; passed: boolean }[] = [
      { id: 'title', label: 'Job Title is filled', passed: title.trim().length > 0 },
      { id: 'dept', label: 'Department is configured', passed: department.trim().length > 0 },
      { id: 'desc', label: 'Role Overview description is filled', passed: overviewText.trim().length > 0 },
      { id: 'responsibilities', label: 'Key Responsibilities are filled', passed: responsibilitiesText.trim().length > 0 },
      { id: 'requirements', label: 'Role Requirements are filled', passed: requirementsText.trim().length > 0 },
      { id: 'manager', label: 'Hiring Manager is assigned', passed: hiringManagerId.trim().length > 0 },
      { id: 'skills', label: 'At least 1 Required Skill is added', passed: requiredSkills.length > 0 },
      { 
        id: 'salary', 
        label: 'Salary constraints are valid', 
        passed: (salaryMin === '' && salaryMax === '') || 
                (salaryMin !== '' && salaryMax !== '' && Number(salaryMax) >= Number(salaryMin) && Number(salaryMin) > 0)
      }
    ]

    const warningsList: { id: string; label: string; passed: boolean }[] = [
      { id: 'location', label: 'Office address is specified', passed: workplaceType === 'Remote' || officeAddress.trim().length > 0 },
      { id: 'benefits', label: 'Perks & Benefits are provided', passed: benefits.length > 0 },
      { id: 'pref-skills', label: 'Preferred skills are provided', passed: preferredSkills.length > 0 },
      { id: 'langs', label: 'Languages are specified', passed: languages.length > 0 },
      { id: 'openings', label: 'Number of openings > 0', passed: openings > 0 }
    ]

    // Calculate live Quality Score (0-100)
    let score = 0
    const recs: string[] = []
    const warns: string[] = []

    // 1. Job Title
    const title_len = title.trim().length
    if (title_len > 0) {
      score += 10
      if (title_len >= 5 && title_len <= 50) {
        score += 5
      } else {
        recs.push('Keep the job title concise (between 5 and 50 characters) to optimize search matches.')
      }
    } else {
      warns.push('Job title is empty. A descriptive title is required before publishing.')
    }

    // 2. Role Description
    const total_desc_len = overviewText.length + responsibilitiesText.length + requirementsText.length
    if (total_desc_len > 300) {
      score += 5
    } else {
      recs.push('Expand the job description context (over 300 characters) to attract higher quality candidates.')
    }

    if (overviewText.trim().length > 100) {
      score += 5
    } else {
      warns.push('Add a detailed Role Overview paragraph.')
    }

    if (responsibilitiesText.trim().length > 0) {
      score += 5
    } else {
      warns.push('Outline the Key Responsibilities section clearly.')
    }

    if (requirementsText.trim().length > 0) {
      score += 5
    } else {
      warns.push('Outline the Requirements & Qualifications section clearly.')
    }

    // 3. Required Skills
    if (requiredSkills.length > 0) {
      score += 15
      if (requiredSkills.length >= 3) {
        score += 5
      } else {
        recs.push('Add at least 3 required skills to enable the AI matching engine to rank candidates accurately.')
      }
    } else {
      warns.push('No required skills added. At least 1 required skill is blocker before publishing.')
    }

    // 4. Salary details
    if (salaryMin !== '' || salaryMax !== '') {
      score += 10
      if (!hideSalary) {
        score += 5
      } else {
        recs.push('Unhide the salary range to increase application conversion rate by up to 30%.')
      }
    } else {
      recs.push('Add a salary range (even if hidden) to help candidates assess fit.')
    }

    // 5. Benefits
    if (benefits.length > 0) {
      score += 10
    } else {
      recs.push('Specify perks & benefits (e.g. Health Insurance, Remote settings) to stand out to top talent.')
    }

    // 6. Hiring Manager
    if (hiringManagerId) {
      score += 10
    } else {
      warns.push('Assign a Hiring Manager to this opening to manage candidate review workflows.')
    }

    // 7. Logistics
    if (workplaceType === 'Remote' || officeAddress.trim().length > 0) {
      score += 5
    } else {
      warns.push('Office address is missing for On-site or Hybrid workplace configuration.')
    }

    if (openings > 0) {
      score += 5
    }

    const allBlockersPassed = blockers.every(b => b.passed)
    return { blockers, warningsList, allBlockersPassed, qualityScore: score, qualityWarnings: warns, qualityRecommendations: recs }
  }

  const { blockers, warningsList, allBlockersPassed, qualityScore, qualityWarnings, qualityRecommendations } = getValidationReport()

  const handlePublish = async () => {
    if (!allBlockersPassed || isPublishing) return
    setIsPublishing(true)
    try {
      const success = await handleAutosave('open')
      if (success) {
        alert('Job posting published successfully!')
        navigate('/recruiter/jobs')
      }
    } catch {
      alert('Failed to publish position.')
    } finally {
      setIsPublishing(false)
    }
  }

  const handleSaveAsDraft = async () => {
    if (isPublishing) return
    setIsPublishing(true)
    try {
      const success = await handleAutosave('draft')
      if (success) {
        alert('Job draft saved successfully!')
        navigate('/recruiter/jobs')
      }
    } catch {
      alert('Failed to save draft.')
    } finally {
      setIsPublishing(false)
    }
  }

  // Construct mock JobFeedItem for exact Candidate Preview rendering parity
  const mockJobFeedItem = {
    title,
    company_name: companyName,
    department,
    description: combineDescription(overviewText, responsibilitiesText, requirementsText),
    start_date: null,
    applicability_score: 100,
    matching_skills: requiredSkills,
    missing_skills: [],
    settings: {
      workplace_type: workplaceType,
      office_address: officeAddress,
      employment_type: employmentType,
      salary_min: salaryMin,
      salary_max: salaryMax,
      currency,
      hide_salary: hideSalary,
      openings,
      benefits
    }
  }

  return (
    <AppLayout>
      {/* Skeleton style overrides */}
      <style>{`
        @keyframes pulse {
          0% { opacity: 0.6; }
          50% { opacity: 1; }
          100% { opacity: 0.6; }
        }
        .skeleton {
          animation: pulse 1.5s infinite ease-in-out;
          background-color: var(--color-cork-shadow);
          border-radius: 4px;
        }
      `}</style>

      <div style={{ maxWidth: '1200px', margin: '0 auto', padding: 'var(--spacing-24) 16px var(--spacing-48)' }}>
        
        {/* Header bar */}
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          borderBottom: '1px solid var(--border)',
          paddingBottom: 'var(--spacing-16)',
          marginBottom: 'var(--spacing-24)',
          gap: '16px'
        }}>
          <div>
            <span style={{ fontSize: 'var(--text-caption)', fontWeight: 550, color: 'var(--color-ash)', letterSpacing: '0.05em', textTransform: 'uppercase' }}>
              Job Openings Command
            </span>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginTop: 4 }}>
              <h1 className="font-signifier" style={{ fontSize: 'var(--text-heading-sm)', fontWeight: 500, color: 'var(--color-ink)', margin: 0, lineHeight: 1.09 }}>
                {title || 'Untitled Draft Opening'}
              </h1>
              <span style={{ 
                fontSize: 11, 
                color: 'var(--color-ash)', 
                fontWeight: 650, 
                display: 'flex', 
                alignItems: 'center', 
                gap: '6px',
                border: '1px solid var(--border)',
                padding: '2px 8px',
                borderRadius: '12px',
                background: 'var(--bg-subtle)'
              }}>
                <span style={{ 
                  width: '6px', 
                  height: '6px', 
                  borderRadius: '50%', 
                  backgroundColor: 
                    saveState === 'saved' ? 'var(--success)' : 
                    saveState === 'saving' ? 'var(--color-rust)' : 
                    saveState === 'unsaved' ? 'var(--color-ash)' : 'var(--danger)'
                }} />
                {saveState === 'saved' && 'Saved'}
                {saveState === 'saving' && 'Saving...'}
                {saveState === 'unsaved' && 'Unsaved changes'}
                {saveState === 'failed' && 'Save failed'}
                {saveState === 'offline' && 'Offline'}
              </span>
            </div>
          </div>
          
          <div style={{ display: 'flex', gap: '8px' }}>
            {editingJobId && (
              <SteepButton 
                variant="secondary" 
                onClick={() => setIsHistoryOpen(true)}
              >
                📜 History
              </SteepButton>
            )}
            <SteepButton 
              variant="secondary" 
              onClick={() => {
                if (hasUnsavedChanges) {
                  setPendingNavigationPath('/recruiter/jobs')
                  setShowNavBlockerModal(true)
                } else {
                  navigate('/recruiter/jobs')
                }
              }}
            >
              Cancel
            </SteepButton>
            <SteepButton variant="primary" onClick={() => handleAutosave()} disabled={saveState === 'saving'}>
              {saveState === 'saving' ? 'Saving...' : 'Save Draft (⌘S)'}
            </SteepButton>
          </div>
        </div>

        {/* Builder Stepper */}
        <div style={{
          display: 'flex',
          flexWrap: 'wrap',
          gap: '8px',
          marginBottom: 'var(--spacing-24)',
          borderBottom: '1px solid var(--border)',
          paddingBottom: '16px'
        }}>
          {[
            '1. Basics',
            '2. Description',
            '3. Skills',
            '4. Compensation',
            '5. Hiring Team',
            '6. Candidate Preview',
            '7. Publish'
          ].map((stepName, index) => {
            const stepNum = index + 1
            const isActive = stepNum === activeStep
            return (
              <button
                key={stepNum}
                onClick={() => navigateToStep(stepNum)}
                style={{
                  padding: '6px 14px',
                  borderRadius: '20px',
                  border: isActive ? '1px solid var(--color-rust)' : '1px solid var(--border)',
                  background: isActive ? 'rgba(93, 42, 26, 0.08)' : 'transparent',
                  color: isActive ? 'var(--color-rust)' : 'var(--color-ash)',
                  fontSize: 'var(--text-caption)',
                  fontWeight: isActive ? 600 : 500,
                  cursor: 'pointer',
                  outline: 'none',
                  transition: 'all 0.15s ease'
                }}
              >
                {stepName}
              </button>
            )
          })}
        </div>

        {/* Main Work Area Container */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'minmax(300px, 1fr) 320px',
          gap: 'var(--spacing-32)',
          alignItems: 'flex-start'
        }}>
          
          {/* Left Work Area */}
          <div>
            {loading ? (
              // Loading skeletons during fetch
              <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
                <div className="skeleton" style={{ height: '48px', width: '40%' }} />
                <div className="skeleton" style={{ height: '180px', width: '100%' }} />
                <div className="skeleton" style={{ height: '48px', width: '100%' }} />
              </div>
            ) : (
              <SteepCard style={{ padding: 'var(--spacing-24) var(--spacing-32)' }}>
                
                {/* Step 1: Basics */}
                {activeStep === 1 && (
                  <div>
                    <h2 style={{ fontSize: 18, fontWeight: 500, margin: '0 0 16px' }}>Job Basics</h2>
                    <SteepInput
                      id="job-title"
                      label="Job Title *"
                      value={title}
                      onChange={e => setTitle(e.target.value)}
                      placeholder="e.g. Lead Software Architect"
                      required
                    />
                    <SteepInput
                      id="job-department"
                      label="Department *"
                      select
                      options={[
                        { value: 'Engineering', label: 'Engineering' },
                        { value: 'Product', label: 'Product Management' },
                        { value: 'Design', label: 'Product Design' },
                        { value: 'Operations', label: 'Operations' },
                        { value: 'Sales', label: 'Sales & Business Development' },
                        { value: 'Marketing', label: 'Marketing' }
                      ]}
                      value={department}
                      onChange={e => setDepartment(e.target.value)}
                      required
                    />
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                      <SteepInput
                        id="job-emp-type"
                        label="Employment Type"
                        select
                        options={[
                          { value: 'Full Time', label: 'Full Time' },
                          { value: 'Part Time', label: 'Part Time' },
                          { value: 'Contract', label: 'Contract' },
                          { value: 'Internship', label: 'Internship' }
                        ]}
                        value={employmentType}
                        onChange={e => setEmploymentType(e.target.value)}
                      />
                      <SteepInput
                        id="job-workplace-type"
                        label="Workplace Setting"
                        select
                        options={[
                          { value: 'On-site', label: 'On-site' },
                          { value: 'Hybrid', label: 'Hybrid' },
                          { value: 'Remote', label: 'Remote' }
                        ]}
                        value={workplaceType}
                        onChange={e => setWorkplaceType(e.target.value)}
                      />
                    </div>
                    {workplaceType !== 'Remote' && (
                      <SteepInput
                        id="job-office-address"
                        label="Office Address"
                        value={officeAddress}
                        onChange={e => setOfficeAddress(e.target.value)}
                        placeholder="City, State / Office Branch Location"
                      />
                    )}
                    <SteepInput
                      id="job-openings"
                      type="number"
                      label="Openings Count"
                      min={1}
                      value={openings}
                      onChange={e => setOpenings(parseInt(e.target.value, 10) || 1)}
                    />
                  </div>
                )}

                {/* Step 2: Description */}
                {activeStep === 2 && (
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                      <h2 style={{ fontSize: 18, fontWeight: 500, margin: 0 }}>Structured Role Description</h2>
                      <SteepButton 
                        variant="secondary" 
                        style={{ border: '1px solid var(--accent)', color: 'var(--accent)' }}
                        onClick={() => setIsAIAssistOpen(true)}
                      >
                        ✍️ AI Assist
                      </SteepButton>
                    </div>
                    
                    {/* Role Overview */}
                    <div style={{ marginBottom: '20px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                          <label className="form-label">Role Overview *</label>
                          {isAIUnaccepted.overview && (
                            <span style={{ fontSize: 9, backgroundColor: '#e6f4ea', color: '#137333', padding: '1px 6px', borderRadius: 10, fontWeight: 600 }}>
                              [AI Generated (Unaccepted)]
                            </span>
                          )}
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                          <button 
                            type="button" 
                            onClick={() => setIsLocked(p => ({ ...p, overview: !p.overview }))}
                            style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 12, color: 'var(--color-ash)' }}
                            title={isLocked.overview ? 'Unlock overview' : 'Lock overview'}
                          >
                            {isLocked.overview ? '🔒 Locked' : '🔓 Lock'}
                          </button>
                          <span style={{ fontSize: '11px', color: 'var(--color-ash)' }}>{overviewText.length} / 5000 chars</span>
                        </div>
                      </div>
                      <textarea
                        value={overviewText}
                        onChange={e => {
                          if (isLocked.overview) return
                          setOverviewText(e.target.value.slice(0, 5000))
                          setIsAIUnaccepted(p => ({ ...p, overview: false }))
                        }}
                        disabled={isLocked.overview}
                        placeholder="Provide a high-level summary introducing candidates to the role and mission..."
                        style={{
                          width: '100%',
                          minHeight: '140px',
                          border: isAIUnaccepted.overview ? '1px solid #a3d9b1' : '1px solid var(--border)',
                          borderRadius: '8px',
                          padding: '12px',
                          fontSize: '14px',
                          fontFamily: 'inherit',
                          outline: 'none',
                          lineHeight: 1.5,
                          background: isAIUnaccepted.overview ? '#f3faf4' : 'transparent',
                          color: 'var(--color-ink)',
                          opacity: isLocked.overview ? 0.65 : 1
                        }}
                      />
                    </div>

                    {/* Key Responsibilities */}
                    <div style={{ marginBottom: '20px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                          <label className="form-label">Key Responsibilities *</label>
                          {isAIUnaccepted.responsibilities && (
                            <span style={{ fontSize: 9, backgroundColor: '#e6f4ea', color: '#137333', padding: '1px 6px', borderRadius: 10, fontWeight: 600 }}>
                              [AI Generated (Unaccepted)]
                            </span>
                          )}
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                          <button 
                            type="button" 
                            onClick={() => setIsLocked(p => ({ ...p, responsibilities: !p.responsibilities }))}
                            style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 12, color: 'var(--color-ash)' }}
                            title={isLocked.responsibilities ? 'Unlock responsibilities' : 'Lock responsibilities'}
                          >
                            {isLocked.responsibilities ? '🔒 Locked' : '🔓 Lock'}
                          </button>
                          <span style={{ fontSize: '11px', color: 'var(--color-ash)' }}>{responsibilitiesText.length} / 5000 chars</span>
                        </div>
                      </div>
                      <textarea
                        value={responsibilitiesText}
                        onChange={e => {
                          if (isLocked.responsibilities) return
                          setResponsibilitiesText(e.target.value.slice(0, 5000))
                          setIsAIUnaccepted(p => ({ ...p, responsibilities: false }))
                        }}
                        disabled={isLocked.responsibilities}
                        placeholder="Bullet points or summary detailing the core tasks this role owns..."
                        style={{
                          width: '100%',
                          minHeight: '140px',
                          border: isAIUnaccepted.responsibilities ? '1px solid #a3d9b1' : '1px solid var(--border)',
                          borderRadius: '8px',
                          padding: '12px',
                          fontSize: '14px',
                          fontFamily: 'inherit',
                          outline: 'none',
                          lineHeight: 1.5,
                          background: isAIUnaccepted.responsibilities ? '#f3faf4' : 'transparent',
                          color: 'var(--color-ink)',
                          opacity: isLocked.responsibilities ? 0.65 : 1
                        }}
                      />
                    </div>

                    {/* Requirements */}
                    <div style={{ marginBottom: '10px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                          <label className="form-label">Requirements & Qualifications *</label>
                          {isAIUnaccepted.requirements && (
                            <span style={{ fontSize: 9, backgroundColor: '#e6f4ea', color: '#137333', padding: '1px 6px', borderRadius: 10, fontWeight: 600 }}>
                              [AI Generated (Unaccepted)]
                            </span>
                          )}
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                          <button 
                            type="button" 
                            onClick={() => setIsLocked(p => ({ ...p, requirements: !p.requirements }))}
                            style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 12, color: 'var(--color-ash)' }}
                            title={isLocked.requirements ? 'Unlock requirements' : 'Lock requirements'}
                          >
                            {isLocked.requirements ? '🔒 Locked' : '🔓 Lock'}
                          </button>
                          <span style={{ fontSize: '11px', color: 'var(--color-ash)' }}>{requirementsText.length} / 5000 chars</span>
                        </div>
                      </div>
                      <textarea
                        value={requirementsText}
                        onChange={e => {
                          if (isLocked.requirements) return
                          setRequirementsText(e.target.value.slice(0, 5000))
                          setIsAIUnaccepted(p => ({ ...p, requirements: false }))
                        }}
                        disabled={isLocked.requirements}
                        placeholder="Education, skills, and background required to be successful..."
                        style={{
                          width: '100%',
                          minHeight: '140px',
                          border: isAIUnaccepted.requirements ? '1px solid #a3d9b1' : '1px solid var(--border)',
                          borderRadius: '8px',
                          padding: '12px',
                          fontSize: '14px',
                          fontFamily: 'inherit',
                          outline: 'none',
                          lineHeight: 1.5,
                          background: isAIUnaccepted.requirements ? '#f3faf4' : 'transparent',
                          color: 'var(--color-ink)',
                          opacity: isLocked.requirements ? 0.65 : 1
                        }}
                      />
                    </div>
                  </div>
                )}

                {/* Step 3: Skills */}
                {activeStep === 3 && (
                  <div>
                    <h2 style={{ fontSize: 18, fontWeight: 500, margin: '0 0 16px' }}>Skills & Criteria</h2>
                    
                    {/* Required skills */}
                    <div style={{ marginBottom: 20 }}>
                      <div style={{ display: 'flex', gap: 12 }}>
                        <div style={{ flex: 1 }}>
                          <SteepInput
                            id="req-skill-input"
                            label="Required Skills (Blocker matching) *"
                            value={reqSkillInput}
                            onChange={e => setReqSkillInput(e.target.value)}
                            placeholder="Add required skill (e.g. Python, SQL)"
                            onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); addTag('req'); } }}
                          />
                        </div>
                        <SteepButton 
                          onClick={() => addTag('req')} 
                          variant="secondary"
                          style={{ marginTop: 24, height: 40 }}
                        >
                          Add
                        </SteepButton>
                      </div>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 8 }}>
                        {requiredSkills.map(s => (
                          <SteepBadge key={s} variant="success" style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                            {s} <button onClick={() => removeTag('req', s)} style={{ border: 'none', background: 'transparent', color: 'inherit', cursor: 'pointer', padding: 0 }}>✕</button>
                          </SteepBadge>
                        ))}
                      </div>
                    </div>

                    {/* Preferred skills */}
                    <div style={{ marginBottom: 20 }}>
                      <div style={{ display: 'flex', gap: 12 }}>
                        <div style={{ flex: 1 }}>
                          <SteepInput
                            id="pref-skill-input"
                            label="Preferred Skills"
                            value={prefSkillInput}
                            onChange={e => setPrefSkillInput(e.target.value)}
                            placeholder="Add nice-to-have skill (e.g. AWS, Redis)"
                            onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); addTag('pref'); } }}
                          />
                        </div>
                        <SteepButton 
                          onClick={() => addTag('pref')} 
                          variant="secondary"
                          style={{ marginTop: 24, height: 40 }}
                        >
                          Add
                        </SteepButton>
                      </div>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 8 }}>
                        {preferredSkills.map(s => (
                          <SteepBadge key={s} variant="neutral" style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                            {s} <button onClick={() => removeTag('pref', s)} style={{ border: 'none', background: 'transparent', color: 'inherit', cursor: 'pointer', padding: 0 }}>✕</button>
                          </SteepBadge>
                        ))}
                      </div>
                    </div>

                    {/* Languages */}
                    <div style={{ marginBottom: 10 }}>
                      <div style={{ display: 'flex', gap: 12 }}>
                        <div style={{ flex: 1 }}>
                          <SteepInput
                            id="lang-input"
                            label="Required Languages"
                            value={langInput}
                            onChange={e => setLangInput(e.target.value)}
                            placeholder="Add language (e.g. English, French)"
                            onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); addTag('lang'); } }}
                          />
                        </div>
                        <SteepButton 
                          onClick={() => addTag('lang')} 
                          variant="secondary"
                          style={{ marginTop: 24, height: 40 }}
                        >
                          Add
                        </SteepButton>
                      </div>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 8 }}>
                        {languages.map(l => (
                          <SteepBadge key={l} variant="neutral" style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                            {l} <button onClick={() => removeTag('lang', l)} style={{ border: 'none', background: 'transparent', color: 'inherit', cursor: 'pointer', padding: 0 }}>✕</button>
                          </SteepBadge>
                        ))}
                      </div>
                    </div>

                    {/* Contextual Recommendations */}
                    <div style={{ marginTop: 24, borderTop: '1px solid var(--border)', paddingTop: 20 }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                        <span style={{ fontSize: 11, fontWeight: 650, color: 'var(--color-rust)', letterSpacing: '0.05em', textTransform: 'uppercase' }}>
                          Contextual Skill Suggestions
                        </span>
                        <button 
                          type="button"
                          onClick={refreshSkillSuggestions}
                          disabled={suggestionsLoading}
                          style={{ fontSize: 11, color: 'var(--color-rust)', background: 'none', border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4 }}
                        >
                          🔄 {suggestionsLoading ? 'Loading Suggestions...' : 'Refresh Suggestions'}
                        </button>
                      </div>
                      
                      {suggestionsLoading ? (
                        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                          <span className="skeleton" style={{ height: 24, width: 80 }} />
                          <span className="skeleton" style={{ height: 24, width: 100 }} />
                          <span className="skeleton" style={{ height: 24, width: 90 }} />
                        </div>
                      ) : skillSuggestions.length > 0 ? (
                        <div>
                          <p style={{ fontSize: 11, color: 'var(--text-secondary)', marginBottom: 8 }}>Click to add as a required tag:</p>
                          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                            {skillSuggestions
                              .filter(s => !requiredSkills.includes(s) && !preferredSkills.includes(s))
                              .map(s => (
                                <button
                                  key={s}
                                  type="button"
                                  onClick={() => setRequiredSkills([...requiredSkills, s])}
                                  style={{
                                    fontSize: 12,
                                    border: '1px solid var(--border)',
                                    padding: '4px 10px',
                                    borderRadius: '16px',
                                    background: 'var(--surface)',
                                    cursor: 'pointer',
                                    transition: 'all 0.15s ease'
                                  }}
                                >
                                  + {s}
                                </button>
                              ))}
                          </div>
                        </div>
                      ) : (
                        <p style={{ fontSize: 12, color: 'var(--text-secondary)', fontStyle: 'italic' }}>
                          Enter a job title on Step 1 to load dynamic suggestions.
                        </p>
                      )}
                    </div>
                  </div>
                )}

                {/* Step 4: Compensation */}
                {activeStep === 4 && (
                  <div>
                    <h2 style={{ fontSize: 18, fontWeight: 500, margin: '0 0 16px' }}>Compensation & Benefits</h2>
                    
                    {/* Live Formatted Compensation Preview */}
                    <div style={{
                      backgroundColor: 'rgba(93, 42, 26, 0.04)',
                      border: '1px dashed var(--color-rust)',
                      borderRadius: '8px',
                      padding: '12px 16px',
                      marginBottom: '20px',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center'
                    }}>
                      <span style={{ fontSize: 13, color: 'var(--color-ash)', fontWeight: 550 }}>Compensation Preview</span>
                      <span style={{ fontSize: 15, fontWeight: 700, color: 'var(--color-rust)' }}>
                        {hideSalary ? (
                          <span style={{ fontSize: 13, color: 'var(--color-ash)', fontStyle: 'italic' }}>Hidden from candidates</span>
                        ) : (
                          (salaryMin !== '' || salaryMax !== '') ? (
                            `${formatSalary(salaryMin, currency)} – ${formatSalary(salaryMax, currency)} / year`
                          ) : (
                            'Not specified'
                          )
                        )}
                      </span>
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                      <SteepInput
                        id="salary-min"
                        type="number"
                        label="Salary Minimum (Annual)"
                        value={salaryMin}
                        onChange={e => setSalaryMin(e.target.value !== '' ? parseInt(e.target.value, 10) : '')}
                        disabled={hideSalary}
                      />
                      <SteepInput
                        id="salary-max"
                        type="number"
                        label="Salary Maximum (Annual)"
                        value={salaryMax}
                        onChange={e => setSalaryMax(e.target.value !== '' ? parseInt(e.target.value, 10) : '')}
                        disabled={hideSalary}
                      />
                    </div>

                    {/* Interactive Salary Range Slider */}
                    {!hideSalary && (
                      <div style={{ margin: '16px 0' }}>
                        <label className="form-label">Salary Range Slider (Max Cap)</label>
                        <div style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
                          <input 
                            type="range" 
                            min={10000} 
                            max={300000} 
                            step={5000}
                            value={salaryMax || 100000}
                            onChange={e => {
                              const val = parseInt(e.target.value, 10)
                              setSalaryMax(val)
                              if (salaryMin !== '' && Number(salaryMin) > val) {
                                setSalaryMin(val)
                              }
                            }}
                            style={{ flex: 1, accentColor: 'var(--color-rust)' }}
                          />
                        </div>
                      </div>
                    )}
                    
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', alignItems: 'center', margin: '8px 0 20px' }}>
                      <SteepInput
                        id="salary-currency"
                        label="Currency"
                        select
                        options={[
                          { value: 'USD', label: 'USD ($)' },
                          { value: 'EUR', label: 'EUR (€)' },
                          { value: 'GBP', label: 'GBP (£)' },
                          { value: 'INR', label: 'INR (₹)' }
                        ]}
                        value={currency}
                        onChange={e => setCurrency(e.target.value)}
                        disabled={hideSalary}
                      />
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 12 }}>
                        <input
                          id="hide-salary"
                          type="checkbox"
                          checked={hideSalary}
                          onChange={e => setHideSalary(e.target.checked)}
                          style={{ cursor: 'pointer', width: 18, height: 18 }}
                        />
                        <label htmlFor="hide-salary" style={{ fontSize: 13, color: 'var(--color-ink)', cursor: 'pointer', userSelect: 'none' }}>
                          Hide salary from candidates
                        </label>
                      </div>
                    </div>

                    {/* Benefits tag list */}
                    <div>
                      <div style={{ display: 'flex', gap: 12 }}>
                        <div style={{ flex: 1 }}>
                          <SteepInput
                            id="benefit-input"
                            label="Perks & Benefits Offered"
                            value={benefitInput}
                            onChange={e => setBenefitInput(e.target.value)}
                            placeholder="Add benefit (e.g. Remote work, Health Insurance)"
                            onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); addTag('benefit'); } }}
                          />
                        </div>
                        <SteepButton 
                          onClick={() => addTag('benefit')} 
                          variant="secondary"
                          style={{ marginTop: 24, height: 40 }}
                        >
                          Add
                        </SteepButton>
                      </div>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 8 }}>
                        {benefits.map(b => (
                          <SteepBadge key={b} variant="neutral" style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                            {b} <button onClick={() => removeTag('benefit', b)} style={{ border: 'none', background: 'transparent', color: 'inherit', cursor: 'pointer', padding: 0 }}>✕</button>
                          </SteepBadge>
                        ))}
                      </div>
                    </div>

                  </div>
                )}

                {/* Step 5: Hiring Team */}
                {activeStep === 5 && (
                  <div>
                    <h2 style={{ fontSize: 18, fontWeight: 500, margin: '0 0 16px' }}>Hiring Team Assignees</h2>
                    
                    <SteepInput
                      id="hiring-manager"
                      label="Hiring Manager *"
                      select
                      options={[
                        { value: '', label: 'Select Hiring Manager...' },
                        ...companyUsers.map(u => ({ value: u.id, label: `${u.full_name} (${u.email})` }))
                      ]}
                      value={hiringManagerId}
                      onChange={e => setHiringManagerId(e.target.value)}
                      required
                    />

                    {/* Recruiters multi-select */}
                    <div style={{ marginBottom: 20 }}>
                      <label className="form-label" style={{ display: 'block', marginBottom: 6 }}>Assigned Recruiters</label>
                      <div style={{ 
                        maxHeight: 140, 
                        overflowY: 'auto', 
                        border: '1px solid var(--border)', 
                        borderRadius: 8, 
                        padding: 10,
                        display: 'flex',
                        flexDirection: 'column',
                        gap: 6
                      }}>
                        {companyUsers.map(u => {
                          const checked = recruiterIds.includes(u.id)
                          return (
                            <label key={u.id} style={{ display: 'flex', alignItems: 'center', gap: 10, fontSize: 13, color: 'var(--color-ink)', cursor: 'pointer' }}>
                              <input
                                type="checkbox"
                                checked={checked}
                                onChange={e => {
                                  if (e.target.checked) {
                                    setRecruiterIds([...recruiterIds, u.id])
                                  } else {
                                    setRecruiterIds(recruiterIds.filter(id => id !== u.id))
                                  }
                                }}
                              />
                              {u.full_name} ({u.email})
                            </label>
                          )
                        })}
                      </div>
                    </div>

                    {/* Interviewers multi-select */}
                    <div>
                      <label className="form-label" style={{ display: 'block', marginBottom: 6 }}>Hiring Interviewers</label>
                      <div style={{ 
                        maxHeight: 140, 
                        overflowY: 'auto', 
                        border: '1px solid var(--border)', 
                        borderRadius: 8, 
                        padding: 10,
                        display: 'flex',
                        flexDirection: 'column',
                        gap: 6
                      }}>
                        {companyUsers.map(u => {
                          const checked = interviewerIds.includes(u.id)
                          return (
                            <label key={u.id} style={{ display: 'flex', alignItems: 'center', gap: 10, fontSize: 13, color: 'var(--color-ink)', cursor: 'pointer' }}>
                              <input
                                type="checkbox"
                                checked={checked}
                                onChange={e => {
                                  if (e.target.checked) {
                                    setInterviewerIds([...interviewerIds, u.id])
                                  } else {
                                    setInterviewerIds(interviewerIds.filter(id => id !== u.id))
                                  }
                                }}
                              />
                              {u.full_name} ({u.email})
                            </label>
                          )
                        })}
                      </div>
                    </div>

                  </div>
                )}

                {/* Step 6: Candidate Preview */}
                {activeStep === 6 && (
                  <div>
                    <h2 style={{ fontSize: 18, fontWeight: 500, margin: '0 0 16px' }}>Candidate View Preview</h2>

                    {/* Publishing Health & Logistics Alert Panel */}
                    <div style={{
                      backgroundColor: 'rgba(93, 42, 26, 0.04)',
                      border: '1px solid var(--border)',
                      borderRadius: '8px',
                      padding: '16px',
                      marginBottom: '20px',
                      fontSize: 13,
                      lineHeight: 1.5,
                      color: 'var(--color-ink)'
                    }}>
                      <h4 style={{ fontSize: 13, fontWeight: 700, margin: '0 0 8px', textTransform: 'uppercase', color: 'var(--color-rust)' }}>
                        Publishing Health & Logistics
                      </h4>
                      <ul style={{ margin: 0, paddingLeft: 20, display: 'flex', flexDirection: 'column', gap: 4 }}>
                        <li><strong>Workplace Setting:</strong> {workplaceType} {workplaceType !== 'Remote' && officeAddress ? `(${officeAddress})` : ''}</li>
                        <li><strong>Employment Type:</strong> {employmentType}</li>
                        <li><strong>Compensation Visibility:</strong> {hideSalary ? 'Salary is hidden from candidate views' : `Salary range visible: ${formatSalary(salaryMin, currency)} – ${formatSalary(salaryMax, currency)}`}</li>
                        <li><strong>Perks & Benefits:</strong> {benefits.length > 0 ? `${benefits.length} perks configured` : 'None specified (adding perks improves candidate conversion)'}</li>
                      </ul>
                    </div>

                    <div style={{ border: '1px solid var(--border)', borderRadius: 12, overflow: 'hidden', background: 'var(--bg)' }}>
                      <JobPreviewHeader
                        title={mockJobFeedItem.title}
                        companyName={mockJobFeedItem.company_name}
                        department={mockJobFeedItem.department}
                      />
                      <div style={{ padding: 'var(--space-6)', display: 'flex', flexDirection: 'column', gap: 'var(--space-6)' }}>
                        <JobPreviewFitRing
                          applicabilityScore={mockJobFeedItem.applicability_score}
                          matchingSkillsCount={mockJobFeedItem.matching_skills.length}
                          totalSkillsCount={mockJobFeedItem.matching_skills.length}
                        />
                        <JobPreviewSkills
                          matchingSkills={mockJobFeedItem.matching_skills}
                          missingSkills={[]}
                        />
                        <JobPreviewDescription
                          description={mockJobFeedItem.description}
                        />
                        <JobPreviewMetadata
                          workplaceType={mockJobFeedItem.settings.workplace_type}
                          employmentType={mockJobFeedItem.settings.employment_type}
                          location={mockJobFeedItem.settings.office_address}
                          salaryMin={mockJobFeedItem.settings.salary_min}
                          salaryMax={mockJobFeedItem.settings.salary_max}
                          currency={mockJobFeedItem.settings.currency}
                          hideSalary={mockJobFeedItem.settings.hide_salary}
                          openings={mockJobFeedItem.settings.openings}
                          benefits={mockJobFeedItem.settings.benefits}
                        />
                      </div>
                    </div>
                  </div>
                )}

                {/* Step 7: Publish controls */}
                {activeStep === 7 && (
                  <div>
                    <h2 style={{ fontSize: 18, fontWeight: 500, margin: '0 0 16px' }}>Publishing Control Dashboard</h2>
                    
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginBottom: '24px' }}>
                      {/* Left: Quality Summary */}
                      <div style={{ padding: '16px', border: '1px solid var(--border)', borderRadius: '8px', background: 'var(--bg-subtle)' }}>
                        <h4 style={{ fontSize: 12, fontWeight: 700, textTransform: 'uppercase', color: 'var(--color-rust)', margin: '0 0 12px' }}>
                          Quality Summary
                        </h4>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 12 }}>
                          <div style={{
                            position: 'relative',
                            width: 60,
                            height: 60,
                            borderRadius: '50%',
                            background: `conic-gradient(var(--color-rust) ${qualityScore}%, var(--color-cork-shadow) ${qualityScore}% 100%)`,
                            display: 'grid',
                            placeItems: 'center'
                          }}>
                            <div style={{
                              width: 48,
                              height: 48,
                              borderRadius: '50%',
                              background: 'var(--surface)',
                              display: 'grid',
                              placeItems: 'center',
                              fontSize: 14,
                              fontWeight: 700
                            }}>
                              {qualityScore}%
                            </div>
                          </div>
                          <div>
                            <span style={{ fontSize: 14, fontWeight: 650, color: 'var(--color-ink)' }}>
                              {qualityScore >= 80 ? 'Excellent Strength' : qualityScore >= 50 ? 'Moderate Strength' : 'Needs Improvement'}
                            </span>
                            <p style={{ fontSize: 11, color: 'var(--color-ash)', margin: '2px 0 0' }}>
                              Ensure all blockers are resolved before publishing.
                            </p>
                          </div>
                        </div>
                        
                        <div style={{ fontSize: 12, display: 'flex', flexDirection: 'column', gap: 4, borderTop: '1px solid var(--border)', paddingTop: 10 }}>
                          <div><strong>Status:</strong> <span style={{ textTransform: 'uppercase', fontWeight: 600, color: 'var(--color-rust)' }}>{jobStatus}</span></div>
                          <div><strong>Last Saved:</strong> {jobUpdatedAt ? new Date(jobUpdatedAt).toLocaleTimeString() : 'Not saved yet'}</div>
                        </div>
                      </div>

                      {/* Right: Validation Checklist Warnings */}
                      <div style={{ padding: '16px', border: '1px solid var(--border)', borderRadius: '8px', background: 'var(--bg-subtle)' }}>
                        <h4 style={{ fontSize: 12, fontWeight: 700, textTransform: 'uppercase', color: 'var(--color-rust)', margin: '0 0 12px' }}>
                          Validation Details
                        </h4>
                        
                        {qualityWarnings.length > 0 ? (
                          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                            {qualityWarnings.map((w, idx) => (
                              <div key={idx} style={{ fontSize: 12, color: 'var(--danger)', display: 'flex', alignItems: 'center', gap: 6 }}>
                                <span>⚠️</span>
                                <span>{w}</span>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <div style={{ fontSize: 12, color: 'var(--success)', display: 'flex', alignItems: 'center', gap: 6 }}>
                            <span>✓</span>
                            <span>All parameters are configured perfectly!</span>
                          </div>
                        )}
                      </div>
                    </div>

                    {!allBlockersPassed && (
                      <div className="banner banner--error" style={{ marginBottom: 24, fontSize: 13 }}>
                        ⚠️ You have outstanding <strong>Blockers</strong> that prevent this job from being published. Please complete all blockers listed in the sidebar.
                      </div>
                    )}

                    <div style={{ display: 'flex', gap: 12, justifyContent: 'flex-end' }}>
                      <SteepButton 
                        variant="secondary" 
                        onClick={handleSaveAsDraft}
                        disabled={isPublishing}
                      >
                        Save as Draft
                      </SteepButton>
                      <SteepButton 
                        variant="primary" 
                        onClick={handlePublish}
                        disabled={!allBlockersPassed || isPublishing}
                      >
                        {isPublishing ? 'Publishing...' : 'Publish Position (⌘Enter)'}
                      </SteepButton>
                    </div>
                  </div>
                )}

                {/* Progressive Actions navigation footer */}
                <div style={{
                  borderTop: '1px solid var(--border)',
                  marginTop: 'var(--spacing-24)',
                  paddingTop: 'var(--spacing-16)',
                  display: 'flex',
                  justifyContent: 'space-between'
                }}>
                  <SteepButton
                    variant="secondary"
                    disabled={activeStep === 1}
                    onClick={() => navigateToStep(activeStep - 1)}
                  >
                    Previous Step
                  </SteepButton>

                  {activeStep < 7 ? (
                    <SteepButton
                      variant="primary"
                      disabled={activeStep === 1 && !title.trim()}
                      onClick={() => navigateToStep(activeStep + 1)}
                    >
                      Next Step
                    </SteepButton>
                  ) : (
                    <div />
                  )}
                </div>

              </SteepCard>
            )}
          </div>

          {/* Right Work Area: Validation Checklist */}
          <div>
            {loading ? (
              // Loading sidebar skeletons
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <div className="skeleton" style={{ height: '36px', width: '80%' }} />
                <div className="skeleton" style={{ height: '200px', width: '100%' }} />
              </div>
            ) : (
              <>
                {/* Desktop view validation checklist card */}
                <div className="desktop-only-checklist">
                  <SteepCard style={{ padding: 20 }}>
                    {/* Live Circular Quality Score Meter */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 20, paddingBottom: 16, borderBottom: '1px solid var(--border)' }}>
                      <div style={{
                        position: 'relative',
                        width: 56,
                        height: 56,
                        borderRadius: '50%',
                        background: `conic-gradient(var(--color-rust) ${qualityScore}%, var(--color-cork-shadow) ${qualityScore}% 100%)`,
                        display: 'grid',
                        placeItems: 'center'
                      }}>
                        <div style={{
                          width: 44,
                          height: 44,
                          borderRadius: '50%',
                          background: 'var(--surface)',
                          display: 'grid',
                          placeItems: 'center',
                          fontSize: 13,
                          fontWeight: 700
                        }}>
                          {qualityScore}%
                        </div>
                      </div>
                      <div>
                        <h4 style={{ fontSize: 13, fontWeight: 600, margin: 0 }}>Posting Strength</h4>
                        <p style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 2 }}>Target &gt;80% for ideal matches</p>
                      </div>
                    </div>

                    <h3 style={{ fontSize: 13, fontWeight: 700, margin: '0 0 16px', letterSpacing: '0.04em', textTransform: 'uppercase', color: 'var(--text-secondary)' }}>
                      Builder Checklist
                    </h3>
                    
                    <div style={{ marginBottom: 16 }}>
                      <span style={{ fontSize: 11, fontWeight: 650, color: 'var(--danger)', display: 'block', marginBottom: 8, letterSpacing: '0.05em', textTransform: 'uppercase' }}>
                        Required Blockers ({blockers.filter(b => b.passed).length}/{blockers.length})
                      </span>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                        {blockers.map(b => (
                          <div key={b.id} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, color: b.passed ? 'var(--success)' : 'var(--color-ash)' }}>
                            <span style={{ fontWeight: 700, fontSize: 14 }}>{b.passed ? '✓' : '•'}</span>
                            <span style={{ textDecoration: b.passed ? 'line-through' : 'none' }}>{b.label}</span>
                          </div>
                        ))}
                      </div>
                    </div>

                    {qualityRecommendations.length > 0 && (
                      <div style={{ marginTop: 16 }}>
                        <span style={{ fontSize: 11, fontWeight: 650, color: 'var(--color-rust)', display: 'block', marginBottom: 8, letterSpacing: '0.05em', textTransform: 'uppercase' }}>
                          Improvement Checklist ({qualityRecommendations.length})
                        </span>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                          {qualityRecommendations.map((r, i) => (
                            <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: 8, fontSize: 11, color: 'var(--text-secondary)' }}>
                              <span style={{ color: 'var(--color-rust)' }}>⚡</span>
                              <span>{r}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                  </SteepCard>
                </div>

                {/* Mobile/Tablet Validation checklist button triggers */}
                <div className="mobile-only-checklist" style={{ marginTop: 12 }}>
                  <SteepButton 
                    variant="secondary" 
                    style={{ width: '100%' }}
                    onClick={() => setIsMobileValidationOpen(true)}
                  >
                    Checklist: {blockers.filter(b => b.passed).length}/{blockers.length} Blockers
                  </SteepButton>
                </div>
              </>
            )}
          </div>

        </div>

      </div>

      {/* 1. SPA Navigation Protection Dialog */}
      {showNavBlockerModal && (
        <div style={{
          position: 'fixed',
          inset: 0,
          background: 'rgba(93, 42, 26, 0.4)',
          backdropFilter: 'blur(4px)',
          display: 'grid',
          placeItems: 'center',
          zIndex: 999,
          padding: 24
        }}>
          <div style={{ maxWidth: 480, width: '100%' }}>
            <SteepCard style={{ padding: 32 }}>
              <h2 className="font-signifier" style={{ fontSize: 24, fontWeight: 500, margin: '0 0 12px', color: 'var(--color-ink)' }}>
                Unsaved Work Detected
              </h2>
              <p style={{ fontSize: 13, color: 'var(--color-ash)', lineHeight: 1.5, margin: '0 0 24px' }}>
                You have unsaved changes in this job posting session. How would you like to proceed?
              </p>
              
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                <SteepButton variant="primary" onClick={() => confirmNavigation('save')}>
                  Save & Leave Page
                </SteepButton>
                <SteepButton variant="secondary" onClick={() => confirmNavigation('discard')}>
                  Leave Without Saving
                </SteepButton>
                <SteepButton variant="secondary" onClick={() => confirmNavigation('cancel')}>
                  Stay & Keep Editing (Esc)
                </SteepButton>
              </div>
            </SteepCard>
          </div>
        </div>
      )}

      {/* 2. Concurrency Conflict Dialog */}
      {showConflictModal && (
        <div style={{
          position: 'fixed',
          inset: 0,
          background: 'rgba(93, 42, 26, 0.4)',
          backdropFilter: 'blur(4px)',
          display: 'grid',
          placeItems: 'center',
          zIndex: 999,
          padding: 24
        }}>
          <div style={{ maxWidth: 480, width: '100%' }}>
            <SteepCard style={{ padding: 32 }}>
              <h2 className="font-signifier" style={{ fontSize: 24, fontWeight: 500, margin: '0 0 12px', color: 'var(--danger)' }}>
                Concurrency Conflict (HTTP 409)
              </h2>
              <p style={{ fontSize: 13, color: 'var(--color-ash)', lineHeight: 1.5, margin: '0 0 24px' }}>
                {conflictErrorMessage || 'This job opening was updated elsewhere by another session.'} Background autosaving is now paused to protect data integrity.
              </p>
              
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                <SteepButton variant="primary" onClick={handleReloadLatest}>
                  Discard Local & Reload Server Copy (Recommended)
                </SteepButton>
                <SteepButton variant="secondary" onClick={() => setShowConflictModal(false)}>
                  Keep Editing Locally (Pauses save)
                </SteepButton>
                <SteepButton 
                  variant="secondary" 
                  style={{ color: 'var(--danger)', borderColor: 'var(--danger)' }}
                  onClick={() => setShowConfirmForceModal(true)}
                >
                  Force Overwrite Server Version (Advanced)
                </SteepButton>
              </div>
            </SteepCard>
          </div>
        </div>
      )}

      {/* 3. Force Overwrite Secondary Confirmation Dialog */}
      {showConfirmForceModal && (
        <div style={{
          position: 'fixed',
          inset: 0,
          background: 'rgba(93, 42, 26, 0.5)',
          backdropFilter: 'blur(6px)',
          display: 'grid',
          placeItems: 'center',
          zIndex: 1000,
          padding: 24
        }}>
          <div style={{ maxWidth: 420, width: '100%' }}>
            <SteepCard style={{ padding: 32, border: '1px solid var(--danger)' }}>
              <h2 className="font-signifier" style={{ fontSize: 20, fontWeight: 500, margin: '0 0 12px', color: 'var(--danger)' }}>
                Confirm Overwrite?
              </h2>
              <p style={{ fontSize: 13, color: 'var(--color-ash)', lineHeight: 1.5, margin: '0 0 24px' }}>
                Warning: Force overwriting will discard the server-side modifications made by the other session. This cannot be undone.
              </p>
              <div style={{ display: 'flex', gap: 12, justifyContent: 'flex-end' }}>
                <SteepButton variant="secondary" onClick={() => setShowConfirmForceModal(false)}>
                  Cancel
                </SteepButton>
                <SteepButton 
                  variant="primary" 
                  style={{ background: 'var(--danger)', color: 'var(--color-pure-white)' }}
                  onClick={handleForceOverwriteSubmit}
                >
                  Yes, Overwrite
                </SteepButton>
              </div>
            </SteepCard>
          </div>
        </div>
      )}

      {/* 4. Mobile Validation Drawer/Modal */}
      {isMobileValidationOpen && (
        <div style={{
          position: 'fixed',
          inset: 0,
          background: 'rgba(93, 42, 26, 0.4)',
          backdropFilter: 'blur(4px)',
          display: 'grid',
          placeItems: 'end',
          zIndex: 999
        }}>
          <div 
            onClick={() => setIsMobileValidationOpen(false)}
            style={{ position: 'absolute', inset: 0 }}
          />
          <div style={{ 
            width: '100%', 
            background: 'var(--bg)', 
            borderTopLeftRadius: 16, 
            borderTopRightRadius: 16,
            padding: 24,
            zIndex: 1000,
            boxShadow: '0 -4px 20px rgba(0,0,0,0.15)',
            maxHeight: '80vh',
            overflowY: 'auto'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
              <h3 style={{ fontSize: 14, fontWeight: 700, margin: 0, letterSpacing: '0.04em', textTransform: 'uppercase', color: 'var(--text-secondary)' }}>
                Builder Checklist
              </h3>
              <button 
                onClick={() => setIsMobileValidationOpen(false)}
                style={{ border: 'none', background: 'transparent', fontSize: 18, color: 'var(--color-ash)', cursor: 'pointer' }}
              >
                ✕
              </button>
            </div>

            <div style={{ marginBottom: 16 }}>
              <span style={{ fontSize: 11, fontWeight: 650, color: 'var(--danger)', display: 'block', marginBottom: 8, letterSpacing: '0.05em', textTransform: 'uppercase' }}>
                Required Blockers
              </span>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {blockers.map(b => (
                  <div key={b.id} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, color: b.passed ? 'var(--success)' : 'var(--color-ash)' }}>
                    <span style={{ fontWeight: 700, fontSize: 14 }}>{b.passed ? '✓' : '•'}</span>
                    <span style={{ textDecoration: b.passed ? 'line-through' : 'none' }}>{b.label}</span>
                  </div>
                ))}
              </div>
            </div>

            <div>
              <span style={{ fontSize: 11, fontWeight: 650, color: 'var(--color-rust)', display: 'block', marginBottom: 8, letterSpacing: '0.05em', textTransform: 'uppercase' }}>
                Recommended Warnings
              </span>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {warningsList.map(w => (
                  <div key={w.id} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, color: w.passed ? 'var(--success)' : 'var(--color-rust)' }}>
                    <span style={{ fontWeight: 700, fontSize: 14 }}>{w.passed ? '✓' : '⚠'}</span>
                    <span>{w.label}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Lazy-loaded Side Drawers */}
      <Suspense fallback={null}>
        {isAIAssistOpen && (
          <AIAssistDrawer
            isOpen={isAIAssistOpen}
            onClose={() => setIsAIAssistOpen(false)}
            jobTitle={title}
            department={department}
            onAcceptSection={handleAcceptAISection}
            onAcceptAll={handleAcceptAllAI}
          />
        )}
        {isHistoryOpen && editingJobId && (
          <RevisionHistoryDrawer
            isOpen={isHistoryOpen}
            onClose={() => setIsHistoryOpen(false)}
            jobId={editingJobId}
            currentValues={{
              title,
              department,
              overviewText,
              responsibilitiesText,
              requirementsText,
              workplaceType,
              employmentType,
              salaryMin,
              salaryMax,
              currency,
              requiredSkills,
              preferredSkills,
              benefits
            }}
          />
        )}
      </Suspense>

      {/* CSS-based responsive styling block */}
      <style>{`
        .desktop-only-checklist {
          display: block;
        }
        .mobile-only-checklist {
          display: none;
        }
        @media (max-width: 768px) {
          .desktop-only-checklist {
            display: none;
          }
          .mobile-only-checklist {
            display: block;
          }
          div[style*="gridTemplateColumns: minmax(300px, 1fr) 320px"] {
            grid-template-columns: 1fr !important;
          }
        }
      `}</style>

    </AppLayout>
  )
}
