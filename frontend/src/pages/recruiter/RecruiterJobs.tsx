import { useState, useEffect, useCallback, useRef } from 'react'
import AppLayout from '../../components/AppLayout'
import { 
  fetchJobs, 
  createJob, 
  updateJob, 
  fetchApplications, 
  generateJobDescription, 
  suggestSkills, 
  type Job, 
  type Application 
} from '../../api'
import SteepCard from '../../components/design-system/SteepCard'
import SteepButton from '../../components/design-system/SteepButton'
import SteepInput from '../../components/design-system/SteepInput'
import SteepBadge from '../../components/design-system/SteepBadge'

export default function RecruiterJobs() {
  const [jobs, setJobs] = useState<Job[]>([])
  const [applications, setApplications] = useState<Application[]>([])
  const [loading, setLoading] = useState(true)

  // Builder Mode State
  const [isBuilding, setIsBuilding] = useState(false)
  const [builderStep, setBuilderStep] = useState(1)
  const [editingJobId, setEditingJobId] = useState<string | null>(null)
  const [jobUpdatedAt, setJobUpdatedAt] = useState<string | null>(null)

  // Step 1: General Details
  const [title, setTitle] = useState('')
  const [dept, setDept] = useState('Engineering')
  const [desc, setDesc] = useState('')

  // Step 2: Compensation & Workplace
  const [employmentType, setEmploymentType] = useState('Full Time')
  const [workplaceType, setWorkplaceType] = useState('On-site')
  const [jobLocation, setJobLocation] = useState('')
  const [salaryMin, setSalaryMin] = useState<number | ''>('')
  const [salaryMax, setSalaryMax] = useState<number | ''>('')
  const [currency, setCurrency] = useState('USD')
  const [relocationOffered, setRelocationOffered] = useState(false)
  const [visaSponsorship, setVisaSponsorship] = useState(false)

  // Custom weights
  const [skillsWeight, setSkillsWeight] = useState(0.40)
  const [experienceWeight, setExperienceWeight] = useState(0.20)
  const [educationWeight, setEducationWeight] = useState(0.10)

  // Step 3: Skills & Criteria
  const [requiredSkills, setRequiredSkills] = useState<string[]>([])
  const [preferredSkills, setPreferredSkills] = useState<string[]>([])
  const [minExperience, setMinExperience] = useState<number | ''>('')
  const [education, setEducation] = useState('Bachelor')
  const [certifications, setCertifications] = useState<string[]>([])
  const [languages, setLanguages] = useState<string[]>([])

  // Skill Input Helpers
  const [newReqSkill, setNewReqSkill] = useState('')
  const [newPrefSkill, setNewPrefSkill] = useState('')
  const [newCert, setNewCert] = useState('')
  const [newLang, setNewLang] = useState('')

  // Suggested skills list (title-based)
  const [suggestedSkillsList, setSuggestedSkillsList] = useState<string[]>([])

  // Step 4: Pipeline Stages
  const [pipelineType, setPipelineType] = useState('Standard Technical')
  const [customStages, setCustomStages] = useState<string[]>(['Parsing', 'Exam', 'Interview', 'Offer'])
  const [newStage, setNewStage] = useState('')

  // Diff / Merge AI state
  const [aiDiffData, setAiDiffData] = useState<{
    description: string
    responsibilities: string[]
    requirements: string[]
    benefits: string[]
  } | null>(null)
  const [isDiffOpen, setIsDiffOpen] = useState(false)
  const [generatingAI, setGeneratingAI] = useState(false)

  // Conflict modal state
  const [conflictError, setConflictError] = useState<string | null>(null)

  // Warnings & Pre-publishing modal
  const [warnings, setWarnings] = useState<string[]>([])
  const [showWarningModal, setShowWarningModal] = useState(false)

  // Autosave track ref to avoid duplicate autosaves
  const isSavingRef = useRef(false)
  const hasChangesRef = useRef(false)

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
      console.error('Error fetching jobs and applications:', err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadData()
  }, [loadData])

  // Contextual Suggested Skills loader
  useEffect(() => {
    if (!title.trim() || title.length < 3) return
    const delayDebounce = setTimeout(async () => {
      try {
        const list = await suggestSkills(title)
        setSuggestedSkillsList(list || [])
      } catch (err) {
        console.error('Failed to load suggested skills:', err)
      }
    }, 800)
    return () => clearTimeout(delayDebounce)
  }, [title])

  // Track state changes to schedule autosave
  useEffect(() => {
    if (isBuilding) {
      hasChangesRef.current = true;
    }
  }, [
    title, dept, desc, employmentType, workplaceType, jobLocation,
    salaryMin, salaryMax, currency, relocationOffered, visaSponsorship,
    skillsWeight, experienceWeight, educationWeight, requiredSkills,
    preferredSkills, minExperience, education, certifications, languages,
    customStages
  ])

  // Autosave Function
  const handleAutosave = useCallback(async (isFinalSubmitStatus?: string) => {
    if (!isBuilding || isSavingRef.current || (!hasChangesRef.current && !isFinalSubmitStatus)) return
    
    isSavingRef.current = true
    try {
      const payloadSettings = {
        employment_type: employmentType,
        workplace_type: workplaceType,
        location: jobLocation,
        salary_min: salaryMin || null,
        salary_max: salaryMax || null,
        currency,
        relocation_offered: relocationOffered,
        visa_sponsorship: visaSponsorship,
        skills_weight: skillsWeight,
        experience_weight: experienceWeight,
        education_weight: educationWeight,
        required_skills: requiredSkills,
        preferred_skills: preferredSkills,
        min_experience_years: minExperience || null,
        education,
        certifications,
        languages,
        stages: customStages
      }

      const payload = {
        title: title || 'Untitled Draft Job',
        department: dept,
        description: desc || 'Draft description.',
        status: isFinalSubmitStatus || 'draft',
        start_date: null,
        settings: payloadSettings,
        client_updated_at: jobUpdatedAt || undefined
      }

      if (editingJobId) {
        const updated = await updateJob(editingJobId, payload)
        setJobUpdatedAt(updated.updated_at)
        hasChangesRef.current = false
      } else {
        const created = await createJob(payload)
        setEditingJobId(created.id)
        setJobUpdatedAt(created.updated_at)
        hasChangesRef.current = false
      }
    } catch (err: any) {
      if (err.response?.status === 409) {
        setConflictError("Optimistic Concurrency Conflict: This job posting has been updated by another recruiter. Overwriting is blocked to protect changes.")
      } else {
        console.error("Autosave failed:", err)
      }
    } finally {
      isSavingRef.current = false
    }
  }, [
    isBuilding, editingJobId, jobUpdatedAt, title, dept, desc, employmentType,
    workplaceType, jobLocation, salaryMin, salaryMax, currency, relocationOffered,
    visaSponsorship, skillsWeight, experienceWeight, educationWeight, requiredSkills,
    preferredSkills, minExperience, education, certifications, languages, customStages
  ])

  // Autosave timer
  useEffect(() => {
    const timer = setInterval(() => {
      handleAutosave()
    }, 20000)
    return () => clearInterval(timer)
  }, [handleAutosave])

  // Trigger manual save immediately on step changes
  const changeStep = async (nextStep: number) => {
    await handleAutosave()
    setBuilderStep(nextStep)
  }

  // Edit action initialization
  const startEditJob = (job: Job) => {
    setEditingJobId(job.id)
    setJobUpdatedAt(job.updated_at)
    setTitle(job.title)
    setDept(job.department)
    setDesc(job.description || '')
    
    const s = job.settings || {}
    setEmploymentType(s.employment_type || 'Full Time')
    setWorkplaceType(s.workplace_type || 'On-site')
    setJobLocation(s.location || '')
    setSalaryMin(s.salary_min || '')
    setSalaryMax(s.salary_max || '')
    setCurrency(s.currency || 'USD')
    setRelocationOffered(s.relocation_offered || false)
    setVisaSponsorship(s.visa_sponsorship || false)
    setSkillsWeight(s.skills_weight ?? 0.40)
    setExperienceWeight(s.experience_weight ?? 0.20)
    setEducationWeight(s.education_weight ?? 0.10)
    setRequiredSkills(s.required_skills || [])
    setPreferredSkills(s.preferred_skills || [])
    setMinExperience(s.min_experience_years || '')
    setEducation(s.education || 'Bachelor')
    setCertifications(s.certifications || [])
    setLanguages(s.languages || [])
    setCustomStages(s.stages || ['Parsing', 'Exam', 'Interview', 'Offer'])
    
    setBuilderStep(1)
    setIsBuilding(true)
  }

  // Create action initialization
  const startCreateJob = () => {
    setEditingJobId(null)
    setJobUpdatedAt(null)
    setTitle('')
    setDept('Engineering')
    setDesc('')
    setEmploymentType('Full Time')
    setWorkplaceType('On-site')
    setJobLocation('')
    setSalaryMin('')
    setSalaryMax('')
    setCurrency('USD')
    setRelocationOffered(false)
    setVisaSponsorship(false)
    setSkillsWeight(0.40)
    setExperienceWeight(0.20)
    setEducationWeight(0.10)
    setRequiredSkills([])
    setPreferredSkills([])
    setMinExperience('')
    setEducation('Bachelor')
    setCertifications([])
    setLanguages([])
    setCustomStages(['Parsing', 'Exam', 'Interview', 'Offer'])
    
    setBuilderStep(1)
    setIsBuilding(true)
  }

  // Toggle status from index list
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

  // AI Description drafting trigger
  const handleAIGenerateDesc = async () => {
    if (!title.trim()) {
      alert("Please enter a job title first.")
      return
    }
    setGeneratingAI(true)
    try {
      const data = await generateJobDescription(title, dept)
      setAiDiffData(data)
      setIsDiffOpen(true)
    } catch (err) {
      alert("AI Generation failed. Reverting to local editor.")
    } finally {
      setGeneratingAI(false)
    }
  }

  // AI Merge choices
  const applyAIMerge = (action: 'replace' | 'append' | 'skills_only') => {
    if (!aiDiffData) return
    
    const formatted = `### Overview
${aiDiffData.description}

### Key Responsibilities
${aiDiffData.responsibilities.map(r => `- ${r}`).join('\n')}

### Role Requirements
${aiDiffData.requirements.map(r => `- ${r}`).join('\n')}

### Perks & Benefits
${aiDiffData.benefits.map(b => `- ${b}`).join('\n')}`

    if (action === 'replace') {
      setDesc(formatted)
      setRequiredSkills(aiDiffData.requirements.map(r => r.split(' ')[0].replace(/[^a-zA-Z]/g, '')).filter(r => r.length > 2).slice(0, 8))
    } else if (action === 'append') {
      setDesc(prev => prev + "\n\n" + formatted)
    } else if (action === 'skills_only') {
      const parsedReqs = aiDiffData.requirements.map(r => r.split(' ')[0].replace(/[^a-zA-Z]/g, '')).filter(r => r.length > 2).slice(0, 8)
      setRequiredSkills(prev => [...new Set([...prev, ...parsedReqs])])
    }
    setIsDiffOpen(false)
  }

  // Publish flow with pre-publishing warning validation
  const triggerPublish = () => {
    const list: string[] = []
    if (requiredSkills.length === 0) {
      list.push("Required Skills: No mandatory skills have been configured. Candidates will not be scored accurately.")
    }
    if (!salaryMin || !salaryMax) {
      list.push("Compensation: Salary ranges are blank. Premium matching relies on location & comp signals.")
    } else if (salaryMin >= salaryMax) {
      list.push("Compensation: Minimum salary is greater than or equal to maximum salary.")
    }

    if (list.length > 0) {
      setWarnings(list)
      setShowWarningModal(true)
    } else {
      finalizePublish()
    }
  }

  const finalizePublish = async () => {
    setShowWarningModal(false)
    setLoading(true)
    try {
      await handleAutosave('open')
      setIsBuilding(false)
      loadData()
    } catch (err) {
      alert("Failed to publish job opening.")
    } finally {
      setLoading(false)
    }
  }

  const handleStagePipelinePreset = (preset: string) => {
    setPipelineType(preset)
    if (preset === 'Standard Technical') {
      setCustomStages(['Parsing', 'Exam', 'Interview', 'Offer'])
    } else if (preset === 'Executive Focus') {
      setCustomStages(['Parsing', 'Panel', 'Offer'])
    } else if (preset === 'General Screening') {
      setCustomStages(['Parsing', 'Phone Call', 'Hire'])
    }
  }

  return (
    <AppLayout>
      {/* 1. Main Job listings index mode */}
      {!isBuilding && (
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
              onClick={startCreateJob}
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
                          onClick={() => startEditJob(job)}
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
        </div>
      )}

      {/* 2. Full-page Progressive Job Builder Mode */}
      {isBuilding && (
        <div style={{ maxWidth: '1000px', margin: '0 auto', padding: '24px 0' }}>
          
          {/* Header & Step progress tracker */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24, borderBottom: '1px solid var(--border)', paddingBottom: 16 }}>
            <div>
              <span style={{ fontSize: 12, color: 'var(--color-ash)', fontWeight: 600 }}>PROGRESSIVE JOB BUILDER</span>
              <h2 className="font-signifier" style={{ fontSize: 24, margin: '4px 0 0', color: 'var(--color-ink)' }}>
                {title || 'Untitled Draft Job'}
              </h2>
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <SteepButton variant="secondary" onClick={async () => { await handleAutosave(); setIsBuilding(false); loadData(); }}>
                Save Draft & Exit
              </SteepButton>
            </div>
          </div>

          {/* Stepper Wizard Bar */}
          <div style={{ display: 'flex', gap: 4, marginBottom: 32 }}>
            {[
              { num: 1, label: "Role Overview" },
              { num: 2, label: "Compensation & Workplace" },
              { num: 3, label: "Target Skills Criteria" },
              { num: 4, label: "Hiring Stages" },
              { num: 5, label: "Candidate Drawer Preview" }
            ].map(s => (
              <div 
                key={s.num} 
                onClick={() => changeStep(s.num)}
                style={{
                  flex: 1,
                  padding: '12px 8px',
                  textAlign: 'center',
                  background: builderStep === s.num ? 'rgba(93, 42, 26, 0.08)' : 'transparent',
                  borderBottom: builderStep === s.num ? '3px solid var(--color-rust)' : '2px solid var(--border)',
                  cursor: 'pointer',
                  transition: 'all 200ms ease'
                }}
              >
                <div style={{ fontSize: 11, fontWeight: 700, color: builderStep === s.num ? 'var(--color-rust)' : 'var(--color-ash)' }}>
                  STEP {s.num}
                </div>
                <div style={{ fontSize: 13, fontWeight: 550, color: 'var(--color-ink)', marginTop: 2 }}>
                  {s.label}
                </div>
              </div>
            ))}
          </div>

          <SteepCard style={{ padding: 32, position: 'relative' }}>
            
            {/* Step 1: Role Overview */}
            {builderStep === 1 && (
              <div>
                <h3 style={{ fontSize: 18, fontWeight: 500, margin: '0 0 16px', color: 'var(--color-ink)' }}>Role Details</h3>
                
                <SteepInput 
                  id="builder-title"
                  label="Job Title"
                  required
                  value={title}
                  onChange={e => setTitle(e.target.value)}
                  placeholder="e.g. Senior Fullstack Engineer"
                />

                {suggestedSkillsList.length > 0 && (
                  <div style={{ marginBottom: 20 }}>
                    <span style={{ fontSize: 12, color: 'var(--color-ash)', display: 'block', marginBottom: 6 }}>
                      🪄 Click to add AI suggested skills to target profile:
                    </span>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                      {suggestedSkillsList.map((skill, idx) => (
                        <button
                          key={idx}
                          type="button"
                          onClick={() => setRequiredSkills(prev => [...new Set([...prev, skill])])}
                          style={{
                            padding: '4px 10px',
                            background: 'var(--bg-subtle)',
                            border: '1px solid var(--border)',
                            borderRadius: '12px',
                            fontSize: '11px',
                            fontWeight: 550,
                            cursor: 'pointer',
                            color: 'var(--color-rust)'
                          }}
                        >
                          + {skill}
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                <SteepInput 
                  id="builder-dept"
                  label="Department"
                  select
                  options={['Engineering', 'Product', 'Design', 'Operations', 'Sales', 'Marketing'].map(d => ({ value: d, label: d }))}
                  value={dept}
                  onChange={e => setDept(e.target.value)}
                />

                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8, marginTop: 16 }}>
                  <label className="form-label" style={{ margin: 0 }}>Role Description</label>
                  <SteepButton 
                    type="button"
                    variant="ghost"
                    onClick={handleAIGenerateDesc}
                    disabled={generatingAI}
                    style={{ fontSize: 12, color: 'var(--color-rust)', border: '1px dashed var(--color-rust)', borderRadius: 12, padding: '4px 12px' }}
                  >
                    {generatingAI ? 'Writing description...' : '🪄 Generate Copyman Draft with AI'}
                  </SteepButton>
                </div>

                <SteepInput 
                  id="builder-desc"
                  required
                  textarea
                  label=""
                  value={desc}
                  onChange={e => setDesc(e.target.value)}
                  placeholder="Provide role overview, requirements and details..."
                  style={{ minHeight: '300px' }}
                />
              </div>
            )}

            {/* Step 2: Compensation & Workplace */}
            {builderStep === 2 && (
              <div>
                <h3 style={{ fontSize: 18, fontWeight: 500, margin: '0 0 16px', color: 'var(--color-ink)' }}>Logistics & Compensation</h3>
                
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>
                  <SteepInput 
                    id="builder-emp-type"
                    label="Employment Type"
                    select
                    options={['Full Time', 'Part Time', 'Contract', 'Internship'].map(t => ({ value: t, label: t }))}
                    value={employmentType}
                    onChange={e => setEmploymentType(e.target.value)}
                  />

                  <SteepInput 
                    id="builder-workplace-type"
                    label="Workplace Setting"
                    select
                    options={['On-site', 'Hybrid', 'Remote'].map(t => ({ value: t, label: t }))}
                    value={workplaceType}
                    onChange={e => setWorkplaceType(e.target.value)}
                  />
                </div>

                <SteepInput 
                  id="builder-location"
                  label="Location"
                  value={jobLocation}
                  onChange={e => setJobLocation(e.target.value)}
                  placeholder="e.g. San Francisco, CA"
                />

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 16, marginTop: 16 }}>
                  <SteepInput 
                    id="builder-sal-min"
                    type="number"
                    label="Minimum Annual Salary"
                    value={salaryMin}
                    onChange={e => setSalaryMin(e.target.value ? parseInt(e.target.value, 10) : '')}
                  />

                  <SteepInput 
                    id="builder-sal-max"
                    type="number"
                    label="Maximum Annual Salary"
                    value={salaryMax}
                    onChange={e => setSalaryMax(e.target.value ? parseInt(e.target.value, 10) : '')}
                  />

                  <SteepInput 
                    id="builder-currency"
                    label="Currency"
                    select
                    options={['USD', 'EUR', 'GBP', 'CAD', 'INR'].map(c => ({ value: c, label: c }))}
                    value={currency}
                    onChange={e => setCurrency(e.target.value)}
                  />
                </div>

                <div style={{ display: 'flex', gap: 32, margin: '24px 0' }}>
                  <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 14, cursor: 'pointer' }}>
                    <input 
                      type="checkbox" 
                      checked={relocationOffered} 
                      onChange={e => setRelocationOffered(e.target.checked)} 
                    />
                    Relocation Assistance Offered
                  </label>

                  <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 14, cursor: 'pointer' }}>
                    <input 
                      type="checkbox" 
                      checked={visaSponsorship} 
                      onChange={e => setVisaSponsorship(e.target.checked)} 
                    />
                    Visa Sponsorship Available
                  </label>
                </div>

                <hr style={{ border: 'none', borderTop: '1px solid var(--border)', margin: '24px 0' }} />

                <h4 style={{ fontSize: 15, fontWeight: 550, margin: '0 0 8px' }}>Personalized Fit Weights (Total sums to 1.0)</h4>
                <p style={{ fontSize: 12, color: 'var(--color-ash)', margin: '0 0 16px' }}>Configure how much each factor impacts a candidate's applicability match score.</p>
                
                <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                  <div>
                    <label style={{ fontSize: 13, fontWeight: 550, display: 'flex', justifyContent: 'space-between' }}>
                      <span>Required Skills Matching Weight</span>
                      <span>{Math.round(skillsWeight * 100)}%</span>
                    </label>
                    <input 
                      type="range" 
                      min="0.10" 
                      max="0.80" 
                      step="0.05"
                      value={skillsWeight}
                      onChange={e => setSkillsWeight(parseFloat(e.target.value))}
                      style={{ width: '100%', accentColor: 'var(--color-rust)' }}
                    />
                  </div>

                  <div>
                    <label style={{ fontSize: 13, fontWeight: 550, display: 'flex', justifyContent: 'space-between' }}>
                      <span>Experience Seniority Weight</span>
                      <span>{Math.round(experienceWeight * 100)}%</span>
                    </label>
                    <input 
                      type="range" 
                      min="0.10" 
                      max="0.60" 
                      step="0.05"
                      value={experienceWeight}
                      onChange={e => setExperienceWeight(parseFloat(e.target.value))}
                      style={{ width: '100%', accentColor: 'var(--color-rust)' }}
                    />
                  </div>

                  <div>
                    <label style={{ fontSize: 13, fontWeight: 550, display: 'flex', justifyContent: 'space-between' }}>
                      <span>Education Degree Weight</span>
                      <span>{Math.round(educationWeight * 100)}%</span>
                    </label>
                    <input 
                      type="range" 
                      min="0.05" 
                      max="0.40" 
                      step="0.05"
                      value={educationWeight}
                      onChange={e => setEducationWeight(parseFloat(e.target.value))}
                      style={{ width: '100%', accentColor: 'var(--color-rust)' }}
                    />
                  </div>
                </div>
              </div>
            )}

            {/* Step 3: Target Criteria */}
            {builderStep === 3 && (
              <div>
                <h3 style={{ fontSize: 18, fontWeight: 500, margin: '0 0 16px', color: 'var(--color-ink)' }}>Ideal Candidate Profile</h3>
                
                {/* Required Skills tags */}
                <div style={{ marginBottom: 20 }}>
                  <label className="form-label">Mandatory Skills (Required)</label>
                  <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
                    <input 
                      type="text"
                      className="input"
                      style={{ flex: 1, padding: '8px 12px', border: '1px solid var(--border)', borderRadius: 12 }}
                      placeholder="Type skill & press Add"
                      value={newReqSkill}
                      onChange={e => setNewReqSkill(e.target.value)}
                      onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); if (newReqSkill.trim()) { setRequiredSkills([...new Set([...requiredSkills, newReqSkill.trim()])]); setNewReqSkill(''); } } }}
                    />
                    <SteepButton type="button" variant="secondary" onClick={() => { if (newReqSkill.trim()) { setRequiredSkills([...new Set([...requiredSkills, newReqSkill.trim()])]); setNewReqSkill(''); } }}>Add</SteepButton>
                  </div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                    {requiredSkills.map((s, idx) => (
                      <span key={idx} style={{ padding: '4px 10px', background: 'rgba(93, 42, 26, 0.08)', borderRadius: 12, fontSize: 12, color: 'var(--color-rust)', display: 'flex', alignItems: 'center', gap: 6 }}>
                        {s}
                        <button type="button" onClick={() => setRequiredSkills(requiredSkills.filter(i => i !== s))} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-rust)' }}>✕</button>
                      </span>
                    ))}
                  </div>
                </div>

                {/* Preferred Skills tags */}
                <div style={{ marginBottom: 20 }}>
                  <label className="form-label">Preferred Skills (Bonus)</label>
                  <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
                    <input 
                      type="text"
                      className="input"
                      style={{ flex: 1, padding: '8px 12px', border: '1px solid var(--border)', borderRadius: 12 }}
                      placeholder="Type preferred skill & press Add"
                      value={newPrefSkill}
                      onChange={e => setNewPrefSkill(e.target.value)}
                      onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); if (newPrefSkill.trim()) { setPreferredSkills([...new Set([...preferredSkills, newPrefSkill.trim()])]); setNewPrefSkill(''); } } }}
                    />
                    <SteepButton type="button" variant="secondary" onClick={() => { if (newPrefSkill.trim()) { setPreferredSkills([...new Set([...preferredSkills, newPrefSkill.trim()])]); setNewPrefSkill(''); } }}>Add</SteepButton>
                  </div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                    {preferredSkills.map((s, idx) => (
                      <span key={idx} style={{ padding: '4px 10px', background: 'var(--bg-subtle)', borderRadius: 12, fontSize: 12, color: 'var(--color-ink)', display: 'flex', alignItems: 'center', gap: 6 }}>
                        {s}
                        <button type="button" onClick={() => setPreferredSkills(preferredSkills.filter(i => i !== s))} style={{ background: 'none', border: 'none', cursor: 'pointer' }}>✕</button>
                      </span>
                    ))}
                  </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>
                  <SteepInput 
                    id="builder-min-exp"
                    type="number"
                    label="Minimum Years of Experience"
                    value={minExperience}
                    onChange={e => setMinExperience(e.target.value ? parseInt(e.target.value, 10) : '')}
                  />

                  <SteepInput 
                    id="builder-edu"
                    label="Target Education Level"
                    select
                    options={['High School', 'Associate', 'Bachelor', 'Master', 'PhD'].map(e => ({ value: e, label: e }))}
                    value={education}
                    onChange={e => setEducation(e.target.value)}
                  />
                </div>

                {/* Certifications */}
                <div style={{ marginBottom: 20, marginTop: 16 }}>
                  <label className="form-label">Required Certifications (Optional)</label>
                  <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
                    <input 
                      type="text"
                      className="input"
                      style={{ flex: 1, padding: '8px 12px', border: '1px solid var(--border)', borderRadius: 12 }}
                      placeholder="e.g. AWS Solutions Architect"
                      value={newCert}
                      onChange={e => setNewCert(e.target.value)}
                      onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); if (newCert.trim()) { setCertifications([...new Set([...certifications, newCert.trim()])]); setNewCert(''); } } }}
                    />
                    <SteepButton type="button" variant="secondary" onClick={() => { if (newCert.trim()) { setCertifications([...new Set([...certifications, newCert.trim()])]); setNewCert(''); } }}>Add</SteepButton>
                  </div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                    {certifications.map((c, idx) => (
                      <span key={idx} style={{ padding: '4px 10px', background: 'var(--bg-subtle)', borderRadius: 12, fontSize: 12, color: 'var(--color-ink)', display: 'flex', alignItems: 'center', gap: 6 }}>
                        {c}
                        <button type="button" onClick={() => setCertifications(certifications.filter(i => i !== c))} style={{ background: 'none', border: 'none', cursor: 'pointer' }}>✕</button>
                      </span>
                    ))}
                  </div>
                </div>

                {/* Languages */}
                <div style={{ marginBottom: 20 }}>
                  <label className="form-label">Languages (Optional)</label>
                  <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
                    <input 
                      type="text"
                      className="input"
                      style={{ flex: 1, padding: '8px 12px', border: '1px solid var(--border)', borderRadius: 12 }}
                      placeholder="e.g. Spanish, German"
                      value={newLang}
                      onChange={e => setNewLang(e.target.value)}
                      onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); if (newLang.trim()) { setLanguages([...new Set([...languages, newLang.trim()])]); setNewLang(''); } } }}
                    />
                    <SteepButton type="button" variant="secondary" onClick={() => { if (newLang.trim()) { setLanguages([...new Set([...languages, newLang.trim()])]); setNewLang(''); } }}>Add</SteepButton>
                  </div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                    {languages.map((l, idx) => (
                      <span key={idx} style={{ padding: '4px 10px', background: 'var(--bg-subtle)', borderRadius: 12, fontSize: 12, color: 'var(--color-ink)', display: 'flex', alignItems: 'center', gap: 6 }}>
                        {l}
                        <button type="button" onClick={() => setLanguages(languages.filter(i => i !== l))} style={{ background: 'none', border: 'none', cursor: 'pointer' }}>✕</button>
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* Step 4: Hiring Flow Stages */}
            {builderStep === 4 && (
              <div>
                <h3 style={{ fontSize: 18, fontWeight: 500, margin: '0 0 16px', color: 'var(--color-ink)' }}>Workflow Pipeline Stages</h3>
                
                <div style={{ marginBottom: 20 }}>
                  <label className="form-label">Pipeline Schema Preset</label>
                  <select
                    value={pipelineType}
                    onChange={e => handleStagePipelinePreset(e.target.value)}
                    style={{
                      width: '100%',
                      background: 'transparent',
                      border: 'none',
                      borderBottom: '1px solid var(--border)',
                      borderRadius: 0,
                      padding: '8px 0',
                      fontSize: 15,
                      color: 'var(--color-ink)',
                      outline: 'none',
                      cursor: 'pointer'
                    }}
                  >
                    <option value="Standard Technical">Standard Technical (Parsing &rarr; Exam &rarr; Interview &rarr; Offer)</option>
                    <option value="Executive Focus">Executive Focus (Parsing &rarr; Panel &rarr; Offer)</option>
                    <option value="General Screening">General Screening (Parsing &rarr; Phone Call &rarr; Hire)</option>
                  </select>
                </div>

                <div style={{ marginBottom: 24 }}>
                  <label className="form-label">Active Flow Stages Sequence</label>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, alignItems: 'center' }}>
                    {customStages.map((stage, idx) => (
                      <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                        <span style={{ padding: '8px 16px', background: 'var(--color-fog)', border: '1px solid var(--border)', borderRadius: 12, fontSize: 13, fontWeight: 550 }}>
                          {stage}
                          {idx > 0 && idx < customStages.length - 1 && (
                            <button 
                              type="button" 
                              onClick={() => setCustomStages(customStages.filter((_, i) => i !== idx))} 
                              style={{ marginLeft: 8, background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-ash)' }}
                            >
                              ✕
                            </button>
                          )}
                        </span>
                        {idx < customStages.length - 1 && <span style={{ color: 'var(--color-ash)' }}>&rarr;</span>}
                      </div>
                    ))}
                  </div>
                </div>

                <div style={{ display: 'flex', gap: 8 }}>
                  <input 
                    type="text"
                    className="input"
                    style={{ flex: 1, padding: '8px 12px', border: '1px solid var(--border)', borderRadius: 12 }}
                    placeholder="Create custom pipeline stage (e.g. Code Review)"
                    value={newStage}
                    onChange={e => setNewStage(e.target.value)}
                  />
                  <SteepButton 
                    type="button" 
                    variant="secondary" 
                    onClick={() => {
                      if (newStage.trim()) {
                        // Insert stage before 'Offer' or at the end
                        const list = [...customStages]
                        const idx = list.indexOf('Offer')
                        if (idx !== -1) {
                          list.splice(idx, 0, newStage.trim())
                        } else {
                          list.push(newStage.trim())
                        }
                        setCustomStages(list)
                        setNewStage('')
                      }
                    }}
                  >
                    Insert Stage
                  </SteepButton>
                </div>
              </div>
            )}

            {/* Step 5: Candidate Drawer Preview */}
            {builderStep === 5 && (
              <div>
                <h3 style={{ fontSize: 18, fontWeight: 500, margin: '0 0 16px', color: 'var(--color-ink)' }}>Live Candidate drawer simulation</h3>
                <p style={{ fontSize: 13, color: 'var(--color-ash)', marginBottom: 24 }}>This shows exactly what the candidate sees in their job feed. Match score ring is previewed assuming candidate profile matching.</p>
                
                <div style={{ border: '1px solid var(--border)', borderRadius: 16, overflow: 'hidden', maxWidth: '560px', margin: '0 auto', background: 'var(--bg)', boxShadow: '0 8px 30px rgba(0,0,0,0.05)' }}>
                  
                  {/* Preview Header */}
                  <div style={{ padding: 24, borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <div>
                      <h4 style={{ fontSize: 18, fontWeight: 800, margin: 0 }}>{title || 'Job Posting Title'}</h4>
                      <p style={{ fontSize: 12, color: 'var(--color-ash)', margin: '4px 0 0' }}>Our Company · <strong>{dept}</strong></p>
                    </div>
                  </div>

                  {/* Preview Body */}
                  <div style={{ padding: 24, display: 'flex', flexDirection: 'column', gap: 20 }}>
                    
                    {/* Ring Chart fit preview */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: 16, padding: 16, background: '#fff', borderRadius: 12, border: '1px solid var(--border)' }}>
                      <div style={{
                        position: 'relative',
                        width: 60,
                        height: 60,
                        borderRadius: '50%',
                        background: 'conic-gradient(var(--color-rust) 80%, var(--color-cork-shadow) 0)',
                        display: 'grid',
                        placeItems: 'center',
                        flexShrink: 0
                      }}>
                        <div style={{ position: 'absolute', inset: 5, borderRadius: '50%', background: '#fff', display: 'grid', placeItems: 'center', fontSize: 13, fontWeight: 800 }}>
                          80%
                        </div>
                      </div>
                      <div>
                        <h5 style={{ fontSize: 14, fontWeight: 750, margin: 0 }}>Personalized Fit (Simulated)</h5>
                        <p style={{ fontSize: 11, color: 'var(--color-ash)', margin: '2px 0 0', lineHeight: 1.3 }}>Matches based on candidate qualifications.</p>
                      </div>
                    </div>

                    {/* Skills matching simulation */}
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                      <h5 style={{ fontSize: 11, fontWeight: 750, color: 'var(--color-ash)', margin: 0, textTransform: 'uppercase' }}>Skills Matching Audit</h5>
                      
                      {requiredSkills.length > 0 ? (
                        <div style={{ display: 'grid', gap: 8 }}>
                          <div style={{ border: '1px solid var(--border)', borderRadius: 12, padding: 12, background: '#fff' }}>
                            <span style={{ fontSize: 11, fontWeight: 750, color: 'var(--success)', display: 'block', marginBottom: 6 }}>✓ Matching Skills (Simulated)</span>
                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                              {requiredSkills.slice(0, Math.ceil(requiredSkills.length * 0.8)).map((s, i) => (
                                <span key={i} style={{ fontSize: 10, padding: '2px 8px', borderRadius: 6, background: 'var(--success-bg)', color: 'var(--success)', fontWeight: 550 }}>{s}</span>
                              ))}
                            </div>
                          </div>

                          {requiredSkills.length > 1 && (
                            <div style={{ border: '1px solid var(--border)', borderRadius: 12, padding: 12, background: '#fff' }}>
                              <span style={{ fontSize: 11, fontWeight: 750, color: 'var(--color-ash)', display: 'block', marginBottom: 6 }}>? Missing Skills (Simulated)</span>
                              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                                {requiredSkills.slice(Math.ceil(requiredSkills.length * 0.8)).map((s, i) => (
                                  <span key={i} style={{ fontSize: 10, padding: '2px 8px', borderRadius: 6, background: 'var(--bg-subtle)', color: 'var(--color-ash)', border: '1px solid var(--border)' }}>{s}</span>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      ) : (
                        <div style={{ fontSize: 12, color: 'var(--color-ash)' }}>No required skills configured. Match ring defaults to 100%.</div>
                      )}
                    </div>

                    {/* Description */}
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                      <h5 style={{ fontSize: 11, fontWeight: 750, color: 'var(--color-ash)', margin: 0, textTransform: 'uppercase' }}>Job Description</h5>
                      <div style={{ fontSize: 13, background: '#fff', padding: 16, borderRadius: 12, border: '1px solid var(--border)', whiteSpace: 'pre-wrap', lineHeight: 1.5 }}>
                        {desc || 'No description provided yet.'}
                      </div>
                    </div>

                    {/* Metadata properties */}
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, background: '#fff', padding: 16, borderRadius: 12, border: '1px solid var(--border)' }}>
                      <div>
                        <span style={{ fontSize: 10, color: 'var(--color-ash)', display: 'block' }}>Setting</span>
                        <strong style={{ fontSize: 12 }}>{workplaceType} ({employmentType})</strong>
                      </div>
                      <div>
                        <span style={{ fontSize: 10, color: 'var(--color-ash)', display: 'block' }}>Salary Range</span>
                        <strong style={{ fontSize: 12 }}>{salaryMin && salaryMax ? `${currency} ${salaryMin.toLocaleString()} - ${salaryMax.toLocaleString()}` : 'Not Specified'}</strong>
                      </div>
                    </div>

                  </div>
                </div>
              </div>
            )}

            {/* Step navigation actions */}
            <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 32, borderTop: '1px solid var(--border)', paddingTop: 24 }}>
              <SteepButton 
                variant="secondary"
                disabled={builderStep === 1}
                onClick={() => changeStep(builderStep - 1)}
              >
                Previous Step
              </SteepButton>

              {builderStep < 5 ? (
                <SteepButton 
                  variant="primary"
                  onClick={() => changeStep(builderStep + 1)}
                >
                  Next Step
                </SteepButton>
              ) : (
                <SteepButton 
                  variant="primary"
                  onClick={triggerPublish}
                >
                  Publish Opening
                </SteepButton>
              )}
            </div>

          </SteepCard>
        </div>
      )}

      {/* 3. AI Diff / Merge View Overlay */}
      {isDiffOpen && aiDiffData && (
        <div style={{
          position: 'fixed',
          inset: 0,
          background: 'rgba(16, 9, 4, 0.7)',
          backdropFilter: 'blur(4px)',
          display: 'grid',
          placeItems: 'center',
          zIndex: 350,
          padding: 24
        }}>
          <div style={{ maxWidth: 800, width: '100%' }}>
            <SteepCard style={{ padding: 32 }}>
              <h2 className="font-signifier" style={{ fontSize: 24, margin: '0 0 16px', color: 'var(--color-ink)' }}>
                🪄 AI Description Diff View
              </h2>
              <p style={{ fontSize: 13, color: 'var(--color-ash)', marginBottom: 20 }}>
                Review draft generated by AI assistant. Decide how you want to merge or append this content.
              </p>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24, maxHeight: 400, overflowY: 'auto', border: '1px solid var(--border)', borderRadius: 12, padding: 16, background: 'var(--bg-subtle)' }}>
                <div>
                  <h4 style={{ fontSize: 12, color: 'var(--color-ash)', textTransform: 'uppercase', marginBottom: 8 }}>Original Text</h4>
                  <div style={{ fontSize: 13, whiteSpace: 'pre-wrap' }}>
                    {desc || '[Empty description]'}
                  </div>
                </div>
                <div>
                  <h4 style={{ fontSize: 12, color: 'var(--color-rust)', textTransform: 'uppercase', marginBottom: 8 }}>AI Suggested Draft</h4>
                  <div style={{ fontSize: 13 }}>
                    <strong>Overview:</strong>
                    <p style={{ margin: '4px 0 12px' }}>{aiDiffData.description}</p>
                    
                    <strong>Responsibilities:</strong>
                    <ul style={{ paddingLeft: 16, margin: '4px 0 12px' }}>
                      {aiDiffData.responsibilities.map((r, i) => <li key={i}>{r}</li>)}
                    </ul>

                    <strong>Requirements:</strong>
                    <ul style={{ paddingLeft: 16, margin: '4px 0 12px' }}>
                      {aiDiffData.requirements.map((r, i) => <li key={i}>{r}</li>)}
                    </ul>

                    <strong>Benefits:</strong>
                    <ul style={{ paddingLeft: 16, margin: '4px 0' }}>
                      {aiDiffData.benefits.map((b, i) => <li key={i}>{b}</li>)}
                    </ul>
                  </div>
                </div>
              </div>

              <div style={{ display: 'flex', gap: 12, justifyContent: 'flex-end', marginTop: 24 }}>
                <SteepButton variant="secondary" onClick={() => setIsDiffOpen(false)}>
                  Cancel
                </SteepButton>
                <SteepButton variant="secondary" onClick={() => applyAIMerge('skills_only')}>
                  Add Requirements to Skills Only
                </SteepButton>
                <SteepButton variant="secondary" onClick={() => applyAIMerge('append')}>
                  Append to End
                </SteepButton>
                <SteepButton variant="primary" onClick={() => applyAIMerge('replace')}>
                  Replace Entirely
                </SteepButton>
              </div>
            </SteepCard>
          </div>
        </div>
      )}

      {/* 4. Concurrency Conflict Modal */}
      {conflictError && (
        <div style={{
          position: 'fixed',
          inset: 0,
          background: 'rgba(239, 68, 68, 0.4)',
          backdropFilter: 'blur(4px)',
          display: 'grid',
          placeItems: 'center',
          zIndex: 400,
          padding: 24
        }}>
          <div style={{ maxWidth: 480, width: '100%' }}>
            <SteepCard style={{ padding: 32, border: '1px solid #ef4444' }}>
              <h2 className="font-signifier" style={{ fontSize: 24, margin: '0 0 16px', color: '#ef4444' }}>
                Conflict Detected
              </h2>
              <p style={{ fontSize: 14, color: 'var(--color-ink)', lineHeight: 1.5, marginBottom: 24 }}>
                {conflictError}
              </p>
              <div style={{ display: 'flex', gap: 12, justifyContent: 'flex-end' }}>
                <SteepButton variant="secondary" onClick={() => { setConflictError(null); setIsBuilding(false); loadData(); }}>
                  Discard My Draft & Reload
                </SteepButton>
                <SteepButton variant="primary" onClick={async () => { setConflictError(null); setJobUpdatedAt(null); hasChangesRef.current = true; await handleAutosave(); }}>
                  Force Overwrite
                </SteepButton>
              </div>
            </SteepCard>
          </div>
        </div>
      )}

      {/* 5. Pre-publishing Verification Warnings Modal */}
      {showWarningModal && (
        <div style={{
          position: 'fixed',
          inset: 0,
          background: 'rgba(16, 9, 4, 0.7)',
          backdropFilter: 'blur(4px)',
          display: 'grid',
          placeItems: 'center',
          zIndex: 360,
          padding: 24
        }}>
          <div style={{ maxWidth: 500, width: '100%' }}>
            <SteepCard style={{ padding: 32, border: '1px solid var(--color-burnt-sienna)' }}>
              <h2 className="font-signifier" style={{ fontSize: 22, margin: '0 0 16px', color: 'var(--color-burnt-sienna)' }}>
                ⚠️ Pre-Publishing Audit Check
              </h2>
              <p style={{ fontSize: 13, color: 'var(--color-ash)', marginBottom: 20 }}>
                We identified some missing signals in your job posting. Do you still want to publish?
              </p>
              
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12, marginBottom: 24 }}>
                {warnings.map((w, idx) => (
                  <div key={idx} style={{ fontSize: 13, color: 'var(--color-ink)', padding: 12, background: 'rgba(217, 119, 6, 0.06)', border: '1px solid rgba(217, 119, 6, 0.15)', borderRadius: 8 }}>
                    {w}
                  </div>
                ))}
              </div>

              <div style={{ display: 'flex', gap: 12, justifyContent: 'flex-end' }}>
                <SteepButton variant="secondary" onClick={() => setShowWarningModal(false)}>
                  Go Back & Fix
                </SteepButton>
                <SteepButton variant="primary" onClick={finalizePublish}>
                  Publish Anyway
                </SteepButton>
              </div>
            </SteepCard>
          </div>
        </div>
      )}

    </AppLayout>
  )
}
