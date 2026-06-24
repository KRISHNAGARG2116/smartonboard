import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import CandidateLayout from '../../components/CandidateLayout'
import CandidateOnboardingWizard from '../../components/CandidateOnboardingWizard'
import AnimatedCounter from '../../components/AnimatedCounter'
import { KpiCardSkeleton, ListRowSkeleton } from '../../components/Skeletons'
import EmptyState from '../../components/EmptyState'
import { motion, type Variants } from 'framer-motion'

import SteepCard from '../../components/design-system/SteepCard'
import SteepButton from '../../components/design-system/SteepButton'
import SteepInput from '../../components/design-system/SteepInput'
import SteepBadge from '../../components/design-system/SteepBadge'
import SteepStatCard from '../../components/design-system/SteepStatCard'

const containerVariants: Variants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: {
      staggerChildren: 0.05
    }
  }
}

const itemVariants: Variants = {
  hidden: { opacity: 0, y: 10 },
  show: {
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.25,
      ease: 'easeOut' as any
    }
  }
}

import {
  fetchCandidateResumes,
  fetchCandidateProfile,
  fetchMyApplications,
  fetchMyInterviews,
  updateCandidateProfile,
  fetchJobFeed,
  type CandidateResume,
  type CandidateApplicationItem,
  type CandidateInterviewItem,
  type JobFeedItem,
  type CandidateMeResponse
} from '../../api'

export default function CandidateDashboard() {
  const { user } = useAuth()
  const navigate = useNavigate()
  
  // Onboarding wizard completion state
  const [hasOnboarded, setHasOnboarded] = useState(() => {
    return localStorage.getItem(`smartonboard_onboarded_candidate_${user?.email}`) === 'true'
  })

  // Core Data States
  const [resumes, setResumes] = useState<CandidateResume[]>([])
  const [applications, setApplications] = useState<CandidateApplicationItem[]>([])
  const [interviews, setInterviews] = useState<CandidateInterviewItem[]>([])
  const [profile, setProfile] = useState<CandidateMeResponse['profile']>(null)
  const [recommendedJobs, setRecommendedJobs] = useState<JobFeedItem[]>([])
  
  // UI Loading/Saving states
  const [loading, setLoading] = useState(true)
  const [submittingBio, setSubmittingBio] = useState(false)
  const [bioSuccess, setBioSuccess] = useState(false)
  
  // Local profile statement (biography) state - synchronized with profile.summary or local storage
  const [bioText, setBioText] = useState('')

  useEffect(() => {
    if (!user) return
    
    // Load initial bio text from localStorage or wait for profile
    const cachedBio = localStorage.getItem(`smartonboard_candidate_bio_${user.email}`) || ''
    setBioText(cachedBio)

    Promise.all([
      fetchCandidateResumes().then(res => setResumes(res)).catch(() => []),
      fetchMyApplications().then(res => setApplications(res)).catch(() => []),
      fetchMyInterviews().then(res => setInterviews(res)).catch(() => []),
      fetchJobFeed(1, 10).then(res => {
        if (res && res.results) {
          setRecommendedJobs(res.results)
        }
      }).catch(() => []),
      fetchCandidateProfile().then(res => {
        if (res && res.profile) {
          setProfile(res.profile)
          if (res.profile.summary) {
            setBioText(res.profile.summary)
          }
        }
      }).catch(() => null)
    ]).finally(() => {
      setLoading(false)
    })
  }, [user])

  if (!hasOnboarded) {
    return (
      <CandidateOnboardingWizard
        onComplete={() => {
          localStorage.setItem(`smartonboard_onboarded_candidate_${user?.email}`, 'true')
          setHasOnboarded(true)
        }}
      />
    )
  }

  // Handle saving profile statement/biography
  const handleSaveBio = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!user) return
    setSubmittingBio(true)
    setBioSuccess(false)
    try {
      // Save locally
      localStorage.setItem(`smartonboard_candidate_bio_${user.email}`, bioText)
      
      // Update backend
      await updateCandidateProfile({
        full_name: profile?.full_name || user?.full_name || '',
        phone_number: profile?.phone_number || undefined,
        location: profile?.location || undefined,
        summary: bioText
      })
      
      setBioSuccess(true)
      setTimeout(() => setBioSuccess(false), 3000)
    } catch (err) {
      console.error('Failed to update biography profile summary', err)
    } finally {
      setSubmittingBio(false)
    }
  }

  // Dynamic calculations
  const emailVerified = profile?.email_verified ?? false
  const phoneVerified = profile?.phone_verified ?? false
  const hasResumes = resumes.length > 0
  const hasBioText = bioText.trim().length > 0

  const profileCompletion = 
    (emailVerified ? 25 : 0) +
    (phoneVerified ? 25 : 0) +
    (hasResumes ? 25 : 0) +
    (hasBioText ? 25 : 0)

  const pendingChecklist = [
    {
      id: 'email',
      title: 'Verify your email address via OTP',
      completed: emailVerified,
      route: '/candidate/profile',
      type: 'verification'
    },
    {
      id: 'phone',
      title: 'Verify your phone number via SMS OTP',
      completed: phoneVerified,
      route: '/candidate/profile',
      type: 'verification'
    },
    {
      id: 'resume',
      title: 'Upload your primary resume to start matching',
      completed: hasResumes,
      route: '/candidate/resumes',
      type: 'resume'
    },
    {
      id: 'bio',
      title: 'Update your professional statement bio',
      completed: hasBioText,
      route: '#bio-form',
      type: 'profile'
    }
  ]

  const activeInterviews = interviews.filter(i => !i.is_cancelled)
  
  // Get active resume and calculate track scores dynamically
  const activeResume = resumes.find(r => r.is_active) || resumes[0]
  const candidateSkills = activeResume?.parsed_skills || []

  const calculateTrackScore = (candSkills: string[], trackSkills: string[], maxRequired = 3) => {
    if (candSkills.length === 0) return 0
    const candSkillsLower = candSkills.map(s => s.toLowerCase())
    const matched = trackSkills.filter(s => candSkillsLower.includes(s.toLowerCase())).length
    return Math.min(100, Math.round((matched / maxRequired) * 100))
  }

  const frontendScore = calculateTrackScore(candidateSkills, ['react', 'angular', 'vue', 'next.js', 'typescript', 'javascript', 'html', 'css', 'tailwind', 'sass', 'graphql'], 3)
  const backendScore = calculateTrackScore(candidateSkills, ['node.js', 'python', 'django', 'flask', 'java', 'spring', 'go', 'golang', 'rust', 'sql', 'postgresql', 'mongodb', 'redis', 'microservices', 'rest api'], 3)
  const devopsScore = calculateTrackScore(candidateSkills, ['aws', 'azure', 'gcp', 'docker', 'kubernetes', 'ci/cd', 'jenkins', 'terraform', 'ansible', 'git', 'github'], 2)
  const dataScore = calculateTrackScore(candidateSkills, ['python', 'sql', 'machine learning', 'deep learning', 'ai', 'tensorflow', 'pytorch', 'pandas', 'numpy'], 2)

  const aggregatedMissingSkills = Array.from(
    new Set(
      recommendedJobs
        .flatMap(job => job.missing_skills || [])
        .map(s => s.trim())
        .filter(s => s.length > 0)
    )
  ).slice(0, 5)

  const missingSkillsToShow = aggregatedMissingSkills.length > 0
    ? aggregatedMissingSkills
    : (hasResumes ? [] : ['Docker', 'AWS', 'Kubernetes'])

  return (
    <CandidateLayout>
      <div style={{ padding: 'var(--spacing-24) 0 var(--spacing-48)' }}>
        {/* Welcome Section */}
        <div style={{ marginBottom: 'var(--spacing-24)' }}>
          <SteepCard variant="default">
            <h1 className="font-signifier" style={{ fontSize: 'var(--text-heading-sm)', fontWeight: 500, color: 'var(--color-ink)', lineHeight: 'var(--leading-heading)', margin: 0 }}>
              Welcome to your Career Hub, {profile?.full_name || user?.full_name || 'Candidate'}!
            </h1>
            <p style={{ color: 'var(--color-ash)', fontSize: 'var(--text-caption)', marginTop: 'var(--spacing-8)', lineHeight: 'var(--leading-normal)', margin: 0 }}>
              Monitor your match strengths, track applications, upload credentials, and stay synced with recruiters.
            </p>
          </SteepCard>
        </div>

        <div className="dashboard-grid" style={{ display: 'grid', gridTemplateColumns: '3fr 1fr', gap: 'var(--spacing-24)' }}>
          {/* Main Content Column */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-24)', minWidth: 0 }}>
            
            {/* Overview Stats Cards */}
            <motion.div 
              variants={containerVariants}
              initial="hidden"
              animate="show"
              style={{ 
                display: 'grid', 
                gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', 
                gap: 'var(--spacing-16)' 
              }}
            >
              {loading ? (
                <>
                  <KpiCardSkeleton />
                  <KpiCardSkeleton />
                  <KpiCardSkeleton />
                </>
              ) : (
                <>
                  {/* Resume Library Card */}
                  <motion.div variants={itemVariants} style={{ display: 'flex', flexDirection: 'column' }}>
                    <Link to="/candidate/resumes" style={{ textDecoration: 'none', display: 'block', height: '100%' }}>
                      <SteepStatCard
                        title="Resume Status"
                        value={`${resumes.length} / 3`}
                        delta={resumes.find(r => r.is_active)?.filename ? `Active: ${resumes.find(r => r.is_active)?.filename}` : 'No active resume set'}
                        icon="📄"
                        style={{ height: '100%', cursor: 'pointer' }}
                      />
                    </Link>
                  </motion.div>

                  {/* Applications Card */}
                  <motion.div variants={itemVariants} style={{ display: 'flex', flexDirection: 'column' }}>
                    <Link to="/candidate/applications" style={{ textDecoration: 'none', display: 'block', height: '100%' }}>
                      <SteepStatCard
                        title="Active Applications"
                        value={applications.length}
                        delta="Submitted applications tracking"
                        icon="📨"
                        style={{ height: '100%', cursor: 'pointer' }}
                      />
                    </Link>
                  </motion.div>

                  {/* Interviews Card */}
                  <motion.div variants={itemVariants} style={{ display: 'flex', flexDirection: 'column' }}>
                    <Link to="/candidate/interviews" style={{ textDecoration: 'none', display: 'block', height: '100%' }}>
                      <SteepStatCard
                        title="Upcoming Interviews"
                        value={activeInterviews.length}
                        delta="Scheduled recruiter synchronization"
                        icon="📅"
                        style={{ height: '100%', cursor: 'pointer' }}
                      />
                    </Link>
                  </motion.div>
                </>
              )}
            </motion.div>

            {/* Setup Checklist */}
            <SteepCard>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--spacing-20)' }}>
                <div>
                  <h3 style={{ fontSize: 'var(--text-body-lg)', fontWeight: 500, color: 'var(--color-ink)', margin: 0 }}>Setup Checklist</h3>
                  <p style={{ fontSize: 'var(--text-caption)', color: 'var(--color-ash)', marginTop: '2px', margin: 0 }}>Complete these steps to verify your identity and start applying.</p>
                </div>
                {pendingChecklist.some(t => !t.completed) ? (
                  <SteepBadge variant="danger">Action Required</SteepBadge>
                ) : (
                  <SteepBadge variant="success">100% Complete</SteepBadge>
                )}
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-12)' }}>
                {loading ? (
                  <>
                    <ListRowSkeleton />
                    <ListRowSkeleton />
                    <ListRowSkeleton />
                  </>
                ) : (
                  pendingChecklist.map((task) => (
                    <div 
                      key={task.id} 
                      style={{ 
                        display: 'flex', 
                        alignItems: 'center', 
                        gap: 'var(--spacing-12)', 
                        padding: 'var(--spacing-12) var(--spacing-16)', 
                        borderRadius: 'var(--radius-inputs)',
                        border: '1px solid var(--border)',
                        background: 'var(--color-pure-white)',
                        opacity: task.completed ? 0.7 : 1
                      }}
                    >
                      <span style={{ fontSize: '16px' }}>{task.completed ? '✅' : '⚠️'}</span>
                      <span style={{ 
                        flex: 1, 
                        fontSize: 'var(--text-body)', 
                        fontWeight: 400, 
                        color: task.completed ? 'var(--color-ash)' : 'var(--color-ink)',
                        textDecoration: task.completed ? 'line-through' : 'none'
                      }}>
                        {task.title}
                      </span>
                      {!task.completed && (
                        task.route.startsWith('#') ? (
                          <SteepButton href={task.route} variant="secondary" size="sm">
                            Resolve
                          </SteepButton>
                        ) : (
                          <SteepButton to={task.route} variant="secondary" size="sm">
                            Resolve
                          </SteepButton>
                        )
                      )}
                    </div>
                  ))
                )}
              </div>
            </SteepCard>

            {/* Match Strength Analysis Section */}
            <SteepCard>
              <div style={{ marginBottom: 'var(--spacing-20)' }}>
                <h3 style={{ fontSize: 'var(--text-body-lg)', fontWeight: 500, color: 'var(--color-ink)', margin: 0 }}>Match Strength Analysis</h3>
                <p style={{ fontSize: 'var(--text-caption)', color: 'var(--color-ash)', marginTop: '2px', margin: 0 }}>
                  Suitability evaluation across common tech pathways based on verified profile qualifications.
                </p>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-16)' }}>
                
                {/* Horizontal Progress Bars */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-12)' }}>
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 'var(--text-body)', marginBottom: '4px' }}>
                      <span style={{ fontWeight: 500, color: 'var(--color-ink)' }}>Frontend Roles</span>
                      <span style={{ color: 'var(--color-rust)', fontWeight: 600 }}><AnimatedCounter value={`${frontendScore}%`} /></span>
                    </div>
                    <div style={{ background: 'var(--color-fog)', height: '8px', borderRadius: '4px', overflow: 'hidden', width: '100%' }}>
                      <div style={{ background: 'var(--color-rust)', height: '100%', width: `${frontendScore}%`, borderRadius: '4px' }} />
                    </div>
                  </div>

                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 'var(--text-body)', marginBottom: '4px' }}>
                      <span style={{ fontWeight: 500, color: 'var(--color-ink)' }}>Backend Roles</span>
                      <span style={{ color: 'var(--color-rust)', fontWeight: 600 }}><AnimatedCounter value={`${backendScore}%`} /></span>
                    </div>
                    <div style={{ background: 'var(--color-fog)', height: '8px', borderRadius: '4px', overflow: 'hidden', width: '100%' }}>
                      <div style={{ background: 'var(--color-rust)', height: '100%', width: `${backendScore}%`, opacity: 0.8, borderRadius: '4px' }} />
                    </div>
                  </div>

                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 'var(--text-body)', marginBottom: '4px' }}>
                      <span style={{ fontWeight: 500, color: 'var(--color-ink)' }}>DevOps Roles</span>
                      <span style={{ color: 'var(--color-ash)', fontWeight: 500 }}><AnimatedCounter value={`${devopsScore}%`} /></span>
                    </div>
                    <div style={{ background: 'var(--color-fog)', height: '8px', borderRadius: '4px', overflow: 'hidden', width: '100%' }}>
                      <div style={{ background: 'var(--color-rust)', height: '100%', width: `${devopsScore}%`, opacity: 0.6, borderRadius: '4px' }} />
                    </div>
                  </div>

                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 'var(--text-body)', marginBottom: '4px' }}>
                      <span style={{ fontWeight: 500, color: 'var(--color-ink)' }}>Data Roles</span>
                      <span style={{ color: 'var(--color-ash)', fontWeight: 500 }}><AnimatedCounter value={`${dataScore}%`} /></span>
                    </div>
                    <div style={{ background: 'var(--color-fog)', height: '8px', borderRadius: '4px', overflow: 'hidden', width: '100%' }}>
                      <div style={{ background: 'var(--color-rust)', height: '100%', width: `${dataScore}%`, opacity: 0.4, borderRadius: '4px' }} />
                    </div>
                  </div>
                </div>

                {/* Top Missing Skills */}
                {missingSkillsToShow.length > 0 && (
                  <div style={{ borderTop: '1px solid var(--border)', paddingTop: 'var(--spacing-16)', marginTop: 'var(--spacing-8)' }}>
                    <h4 style={{ fontSize: 'var(--text-caption)', fontWeight: 650, color: 'var(--color-ash)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '8px' }}>
                      Top Missing Skills
                    </h4>
                    <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                      {missingSkillsToShow.map((skill: string) => (
                        <SteepBadge key={skill} variant="neutral">
                          {skill}
                        </SteepBadge>
                      ))}
                    </div>
                  </div>
                )}

              </div>
            </SteepCard>

            {/* Recommended Matching Jobs */}
            <SteepCard>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--spacing-20)' }}>
                <div>
                  <h3 style={{ fontSize: 'var(--text-body-lg)', fontWeight: 500, color: 'var(--color-ink)', margin: 0 }}>Recommended Matching Jobs</h3>
                  <p style={{ fontSize: 'var(--text-caption)', color: 'var(--color-ash)', marginTop: '2px', margin: 0 }}>Matching positions aligned with your skillset from active jobs.</p>
                </div>
                <Link to="/candidate/jobs" style={{ fontSize: 'var(--text-caption)', color: 'var(--color-rust)', textDecoration: 'underline', textUnderlineOffset: 3 }}>Explore Feed &rarr;</Link>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-12)' }}>
                {loading ? (
                  <>
                    <ListRowSkeleton />
                    <ListRowSkeleton />
                  </>
                ) : recommendedJobs.length > 0 ? (
                  recommendedJobs.slice(0, 3).map((job) => (
                    <div key={job.id} style={{
                      border: '1px solid var(--border)',
                      borderRadius: 'var(--radius-inputs)',
                      padding: 'var(--spacing-16)',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      background: 'var(--color-pure-white)'
                    }}>
                      <div>
                        <h4 style={{ fontSize: '15px', fontWeight: 500, color: 'var(--color-ink)', margin: 0 }}>{job.title}</h4>
                        <span style={{ fontSize: 'var(--text-caption)', color: 'var(--color-ash)' }}>{job.company_name} &bull; {job.department}</span>
                        <div style={{ marginTop: '8px', display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                          {(job.matching_skills || []).slice(0, 3).map((skill: string) => (
                            <SteepBadge key={skill} variant="neutral">{skill}</SteepBadge>
                          ))}
                        </div>
                      </div>
                      <div style={{ textAlign: 'right' }}>
                        <div style={{ fontSize: '16px', fontWeight: 600, color: 'var(--color-rust)', marginBottom: 'var(--spacing-8)' }}>
                          {job.applicability_score}% Match
                        </div>
                        <SteepButton to="/candidate/jobs" variant="secondary" size="sm">
                          View &amp; Apply
                        </SteepButton>
                      </div>
                    </div>
                  ))
                ) : (
                  <EmptyState
                     type="jobs"
                     title="No Job Matches Found"
                     description="No job recommendations currently fit your profile. Set your active resume or check the full job feed."
                     actionLabel="View All Jobs"
                     onAction={() => navigate('/candidate/jobs')}
                  />
                )}
              </div>
            </SteepCard>

            {/* Upcoming Interviews Calendar Booking Widget */}
            <SteepCard>
              <div style={{ marginBottom: 'var(--spacing-20)' }}>
                <h3 style={{ fontSize: 'var(--text-body-lg)', fontWeight: 500, color: 'var(--color-ink)', margin: 0 }}>Upcoming Interviews &amp; Scheduling</h3>
                <p style={{ fontSize: 'var(--text-caption)', color: 'var(--color-ash)', marginTop: '2px', margin: 0 }}>
                  Coordinate your live video screening calls and technical reviews.
                </p>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-16)' }}>
                {loading ? (
                  <>
                    <ListRowSkeleton />
                    <ListRowSkeleton />
                  </>
                ) : activeInterviews.length > 0 ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-12)' }}>
                    {activeInterviews.map((iv) => (
                      <div 
                        key={iv.id}
                        style={{
                          border: '1px solid var(--border)',
                          borderRadius: 'var(--radius-inputs)',
                          padding: 'var(--spacing-16)',
                          background: 'var(--color-pure-white)'
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                          <div>
                            <SteepBadge variant="interview" style={{ marginBottom: 'var(--spacing-8)' }}>{iv.stage}</SteepBadge>
                            <h4 style={{ fontSize: '16px', fontWeight: 500, color: 'var(--color-ink)', margin: 0 }}>{iv.title}</h4>
                            <p style={{ fontSize: 'var(--text-caption)', color: 'var(--color-ash)', marginTop: '4px', margin: 0 }}>
                              🏢 {iv.company_name} &bull; 👤 {iv.interviewer_name}
                            </p>
                          </div>
                          <div style={{ textAlign: 'right' }}>
                            <span style={{ fontSize: 'var(--text-caption)', fontWeight: 600, color: 'var(--color-rust)' }}>
                              {new Date(iv.scheduled_at).toLocaleDateString([], { month: 'short', day: 'numeric' })} at {new Date(iv.scheduled_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                            </span>
                          </div>
                        </div>
                        {iv.video_link && (
                          <div style={{ marginTop: '12px', display: 'flex', gap: '8px' }}>
                            <SteepButton 
                              href={iv.video_link} 
                              target="_blank" 
                              rel="noreferrer" 
                              variant="primary" 
                              size="sm"
                            >
                              Join Call
                            </SteepButton>
                            <SteepButton to="/candidate/interviews" variant="secondary" size="sm">
                              Reschedule
                            </SteepButton>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <EmptyState
                    type="interviews"
                    title="No Coordinated Interviews"
                    description="No live panels are currently active. When a recruiter invites you to schedule, options will appear here."
                    actionLabel="View My Calendar"
                    onAction={() => navigate('/candidate/interviews')}
                  />
                )}
              </div>
            </SteepCard>

          </div>

          {/* Right Sidebar Column */}
          <div className="dashboard-sidebar" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-24)' }}>
            
            {/* Profile Completion Circular Conic Card (Warm Apricot Wash) */}
            <SteepCard variant="warm">
              <h3 style={{ fontSize: 'var(--text-caption)', fontWeight: 600, color: 'var(--color-rust)', textTransform: 'uppercase', letterSpacing: '0.05em', margin: 0 }}>
                Profile Completion
              </h3>
              
              <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--spacing-16)', marginTop: 'var(--spacing-16)' }}>
                {/* Conic circular progress indicator */}
                <div 
                  style={{ 
                    position: 'relative', 
                    width: '64px', 
                    height: '64px', 
                    borderRadius: '50%', 
                    background: `conic-gradient(var(--color-rust) ${profileCompletion}%, rgba(93, 42, 26, 0.1) 0)`,
                    display: 'grid',
                    placeItems: 'center',
                    flexShrink: 0
                  }}
                >
                  <div 
                    style={{ 
                      position: 'absolute', 
                      inset: '6px', 
                      borderRadius: '50%', 
                      background: 'var(--surface-warm-tint)', 
                      display: 'grid', 
                      placeItems: 'center',
                      fontSize: '13px',
                      fontWeight: 600,
                      color: 'var(--color-rust)'
                    }}
                  >
                    <AnimatedCounter value={`${profileCompletion}%`} />
                  </div>
                </div>

                <div>
                  <h4 style={{ fontSize: '14px', fontWeight: 500, color: 'var(--color-rust)', margin: 0 }}>
                    {profileCompletion === 100 ? 'Profile Verified!' : 'Complete Setup'}
                  </h4>
                  <p style={{ fontSize: '11px', color: 'var(--color-rust)', marginTop: '4px', margin: 0, lineHeight: 1.3, opacity: 0.8 }}>
                    {profileCompletion === 100 
                      ? 'Congratulations, you have unlocked 100% of your Career Hub capabilities!'
                      : 'Verify phone OTP and add biography statement to hit 100% matches.'
                    }
                  </p>
                </div>
              </div>
            </SteepCard>

            {/* Verification Center (Cool Sky Wash) */}
            <SteepCard variant="cool">
              <h3 style={{ fontSize: 'var(--text-caption)', fontWeight: 600, color: 'var(--color-ink)', textTransform: 'uppercase', letterSpacing: '0.05em', margin: 0, marginBottom: 'var(--spacing-16)' }}>
                Verification Center
              </h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-12)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 'var(--text-body)' }}>
                  <span style={{ color: 'var(--color-ink)' }}>Email Status</span>
                  <SteepBadge variant={emailVerified ? 'success' : 'danger'}>
                    {emailVerified ? 'Verified' : 'Unverified'}
                  </SteepBadge>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 'var(--text-body)' }}>
                  <span style={{ color: 'var(--color-ink)' }}>Phone Status</span>
                  <SteepBadge variant={phoneVerified ? 'success' : 'warning'}>
                    {phoneVerified ? 'Verified' : 'Unverified'}
                  </SteepBadge>
                </div>
              </div>
            </SteepCard>

            {/* Quick Actions Panel */}
            <SteepCard>
              <h3 style={{ fontSize: 'var(--text-caption)', fontWeight: 650, color: 'var(--color-ash)', textTransform: 'uppercase', letterSpacing: '0.05em', margin: 0, marginBottom: 'var(--spacing-16)' }}>
                Quick Actions
              </h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                <SteepButton to="/candidate/resumes" variant="primary" size="sm" block>
                  Upload New Resume (Max 3)
                </SteepButton>
                <SteepButton to="/candidate/profile" variant="secondary" size="sm" block>
                  Verify Phone &amp; Email OTP
                </SteepButton>
                <SteepButton to="/candidate/jobs" variant="secondary" size="sm" block>
                  Search Open Roles
                </SteepButton>
              </div>
            </SteepCard>

            {/* Profile Statement Updates Form */}
            <form id="bio-form" onSubmit={handleSaveBio}>
              <SteepCard>
                <h3 style={{ fontSize: 'var(--text-caption)', fontWeight: 650, color: 'var(--color-ash)', textTransform: 'uppercase', letterSpacing: '0.05em', margin: 0, marginBottom: 'var(--spacing-16)' }}>
                  Biography Statement
                </h3>
                {bioSuccess && (
                  <div style={{ fontSize: 'var(--text-caption)', color: 'var(--color-ink)', border: '1px solid var(--border)', padding: '6px 10px', borderRadius: 'var(--radius-tags)', marginBottom: 'var(--spacing-12)' }}>
                    ✅ Statement saved successfully!
                  </div>
                )}
                <SteepInput
                  textarea
                  id="bio-textarea"
                  label="Career Bio Statement"
                  value={bioText}
                  onChange={(e) => setBioText(e.target.value)}
                  placeholder="Describe your technical background..."
                  required
                  style={{ minHeight: '80px', fontSize: '12.5px' }}
                />
                <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 'var(--spacing-12)' }}>
                  <SteepButton type="submit" variant="primary" size="sm" disabled={submittingBio}>
                    {submittingBio ? 'Saving...' : 'Save Statement'}
                  </SteepButton>
                </div>
              </SteepCard>
            </form>

            {/* Resume Improvement Suggestions */}
            <SteepCard>
              <h3 style={{ fontSize: 'var(--text-caption)', fontWeight: 650, color: 'var(--color-ash)', textTransform: 'uppercase', letterSpacing: '0.05em', margin: 0, marginBottom: 'var(--spacing-16)' }}>
                Resume Diagnostics
              </h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', fontSize: '12px', lineHeight: 1.35 }}>
                <div style={{ color: 'var(--color-ink)' }}>
                  💡 <strong style={{ color: 'var(--color-rust)' }}>Boost DevOps Match:</strong> Mentioning <strong>Docker</strong> or <strong>Kubernetes</strong> on your resume could increase your DevOps alignment by 25%.
                </div>
                <div style={{ color: 'var(--color-ink)' }}>
                  💡 <strong style={{ color: 'var(--color-rust)' }}>Specify Frameworks:</strong> Ensure <strong>React</strong> and <strong>TypeScript</strong> are explicitly written in your core technical experience sections section.
                </div>
                <div style={{ color: 'var(--color-ink)' }}>
                  💡 <strong>Verification Boost:</strong> Fully verified candidates (Email + Phone SMS OTP) are highlighted to recruiters and experience 3x faster reviews.
                </div>
                <div style={{ color: 'var(--color-ink)' }}>
                  💡 <strong>Target Roles:</strong> You can upload up to 3 separate CV documents to optimize matching for different pathways.
                </div>
              </div>
            </SteepCard>

          </div>
        </div>
      </div>
    </CandidateLayout>
  )
}
