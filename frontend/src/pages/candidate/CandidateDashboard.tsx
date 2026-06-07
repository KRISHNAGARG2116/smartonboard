import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import CandidateLayout from '../../components/CandidateLayout'
import CandidateOnboardingWizard from '../../components/CandidateOnboardingWizard'
import {
  fetchCandidateResumes,
  fetchCandidateProfile,
  fetchMyApplications,
  fetchMyInterviews,
  updateCandidateProfile,
  fetchJobFeed
} from '../../api'

export default function CandidateDashboard() {
  const { user } = useAuth()
  
  // Onboarding wizard completion state
  const [hasOnboarded, setHasOnboarded] = useState(() => {
    return localStorage.getItem(`smartonboard_onboarded_candidate_${user?.email}`) === 'true'
  })

  // Core Data States
  const [resumes, setResumes] = useState<any[]>([])
  const [applications, setApplications] = useState<any[]>([])
  const [interviews, setInterviews] = useState<any[]>([])
  const [profile, setProfile] = useState<any>(null)
  const [recommendedJobs, setRecommendedJobs] = useState<any[]>([])
  
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
          } else if (cachedBio) {
            // Keep the cached bio
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
  const candidateSkills = activeResume?.parsed_skills || profile?.skills || []

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
      <div className="container" style={{ padding: 'var(--space-6) 0 var(--space-12)' }}>
        {/* Welcome Section */}
        <div 
          className="card" 
          style={{ 
            background: 'transparent', 
            padding: 'var(--space-6)', 
            border: '1px dashed var(--color-cork-shadow)',
            borderRadius: '12px',
            marginBottom: 'var(--space-6)',
            boxShadow: 'none'
          }}
        >
          <h1 style={{ fontSize: 'var(--text-heading)', fontWeight: 500, letterSpacing: '-0.02em', color: 'var(--text)', lineHeight: 'var(--leading-heading)' }}>
            Welcome to your Career Hub, {profile?.full_name || user?.full_name || 'Candidate'}!
          </h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-sm)', marginTop: 'var(--space-1)', lineHeight: 'var(--leading-normal)' }}>
            Monitor your match strengths, track applications, upload credentials, and stay synced with recruiters.
          </p>
        </div>

        <div className="dashboard-grid">
          {/* Main Content Column */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)', minWidth: 0 }}>
            
            {/* Overview Stats Cards */}
            <div 
              style={{ 
                display: 'grid', 
                gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', 
                gap: 'var(--space-4)' 
              }}
            >
              {/* Resume Library Card */}
              <Link to="/candidate/resumes" className="card card__body" style={{ textDecoration: 'none', background: 'transparent' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-secondary)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Resume Status</span>
                  <span style={{ fontSize: '18px' }}>📄</span>
                </div>
                <div style={{ fontSize: 'var(--text-3xl)', fontWeight: 600, marginTop: 'var(--space-3)', color: 'var(--text)' }}>
                  {resumes.length} <span style={{ fontSize: 'var(--text-sm)', color: 'var(--text-tertiary)', fontWeight: 400 }}>/ 3 Uploaded</span>
                </div>
                <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: 'var(--space-2)' }}>
                  {resumes.find(r => r.is_active)?.filename ? `Active: ${resumes.find(r => r.is_active)?.filename}` : 'No active resume set'}
                </div>
              </Link>

              {/* Applications Card */}
              <Link to="/candidate/applications" className="card card__body" style={{ textDecoration: 'none', background: 'transparent' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-secondary)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Active Applications</span>
                  <span style={{ fontSize: '18px' }}>📨</span>
                </div>
                <div style={{ fontSize: 'var(--text-3xl)', fontWeight: 600, marginTop: 'var(--space-3)', color: 'var(--text)' }}>
                  {applications.length}
                </div>
                <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: 'var(--space-2)' }}>
                  Submitted applications tracking
                </div>
              </Link>

              {/* Interviews Card */}
              <Link to="/candidate/interviews" className="card card__body" style={{ textDecoration: 'none', background: 'transparent' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-secondary)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Upcoming Interviews</span>
                  <span style={{ fontSize: '18px' }}>📅</span>
                </div>
                <div style={{ fontSize: 'var(--text-3xl)', fontWeight: 600, marginTop: 'var(--space-3)', color: 'var(--text)' }}>
                  {activeInterviews.length}
                </div>
                <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: 'var(--space-2)' }}>
                  Scheduled recruiter synchronization
                </div>
              </Link>
            </div>

            {/* Setup Checklist */}
            <div className="card" style={{ background: 'transparent' }}>
              <div className="card__header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <h3 style={{ fontSize: 'var(--text-lg)', fontWeight: 500, color: 'var(--text)', margin: 0 }}>Setup Checklist</h3>
                  <p style={{ fontSize: 'var(--text-xs)', color: 'var(--text-secondary)', marginTop: '2px', margin: 0 }}>Complete these steps to verify your identity and start applying.</p>
                </div>
                {pendingChecklist.some(t => !t.completed) ? (
                  <span className="badge badge--reject">Action Required</span>
                ) : (
                  <span className="badge badge--hire">100% Complete</span>
                )}
              </div>
              <div className="card__body" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
                {loading ? (
                  <div style={{ padding: 'var(--space-4)', textAlign: 'center', color: 'var(--text-secondary)' }}>
                    Loading checklist...
                  </div>
                ) : (
                  pendingChecklist.map((task) => (
                    <div 
                      key={task.id} 
                      style={{ 
                        display: 'flex', 
                        alignItems: 'center', 
                        gap: 'var(--space-3)', 
                        padding: 'var(--space-3)', 
                        background: 'transparent', 
                        borderRadius: 'var(--radius-xl)',
                        border: '1px dashed var(--color-cork-shadow)',
                        opacity: task.completed ? 0.7 : 1
                      }}
                    >
                      <span style={{ fontSize: '16px' }}>{task.completed ? '✅' : '⚠️'}</span>
                      <span style={{ 
                        flex: 1, 
                        fontSize: 'var(--text-sm)', 
                        fontWeight: 400, 
                        color: task.completed ? 'var(--text-secondary)' : 'var(--text)',
                        textDecoration: task.completed ? 'line-through' : 'none'
                      }}>
                        {task.title}
                      </span>
                      {!task.completed && (
                        task.route.startsWith('#') ? (
                          <a 
                            href={task.route} 
                            className="btn btn--accent btn--sm" 
                            style={{ 
                              borderRadius: 'var(--radius-buttons-rounded)',
                              padding: '6px 14px',
                              background: 'var(--color-dark-cork)',
                              color: 'var(--text)',
                              border: 'none'
                            }}
                          >
                            Resolve
                          </a>
                        ) : (
                          <Link 
                            to={task.route} 
                            className="btn btn--accent btn--sm" 
                            style={{ 
                              borderRadius: 'var(--radius-buttons-rounded)',
                              padding: '6px 14px',
                              background: 'var(--color-dark-cork)',
                              color: 'var(--text)',
                              border: 'none'
                            }}
                          >
                            Resolve
                          </Link>
                        )
                      )}
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Match Strength Analysis Section */}
            <div className="card" style={{ background: 'transparent' }}>
              <div className="card__header">
                <h3 style={{ fontSize: 'var(--text-lg)', fontWeight: 500, color: 'var(--text)', margin: 0 }}>Match Strength Analysis</h3>
                <p style={{ fontSize: 'var(--text-xs)', color: 'var(--text-secondary)', marginTop: '2px', margin: 0 }}>
                  Suitability evaluation across common tech pathways based on verified profile qualifications.
                </p>
              </div>
              <div className="card__body" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
                
                {/* Horizontal Progress Bars */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 'var(--text-sm)', marginBottom: '4px' }}>
                      <span style={{ fontWeight: 500 }}>Frontend Roles</span>
                      <span style={{ color: 'var(--color-burnt-sienna)', fontWeight: 650 }}>{frontendScore}%</span>
                    </div>
                    <div style={{ background: 'var(--color-cork-shadow)', height: '8px', borderRadius: '4px', overflow: 'hidden', width: '100%' }}>
                      <div style={{ background: 'var(--color-burnt-sienna)', height: '100%', width: `${frontendScore}%`, borderRadius: '4px' }} />
                    </div>
                  </div>

                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 'var(--text-sm)', marginBottom: '4px' }}>
                      <span style={{ fontWeight: 500 }}>Backend Roles</span>
                      <span style={{ color: 'var(--text)', fontWeight: 600 }}>{backendScore}%</span>
                    </div>
                    <div style={{ background: 'var(--color-cork-shadow)', height: '8px', borderRadius: '4px', overflow: 'hidden', width: '100%' }}>
                      <div style={{ background: 'var(--color-burnt-sienna)', height: '100%', width: `${backendScore}%`, opacity: 0.8, borderRadius: '4px' }} />
                    </div>
                  </div>

                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 'var(--text-sm)', marginBottom: '4px' }}>
                      <span style={{ fontWeight: 500 }}>DevOps Roles</span>
                      <span style={{ color: 'var(--text-secondary)', fontWeight: 500 }}>{devopsScore}%</span>
                    </div>
                    <div style={{ background: 'var(--color-cork-shadow)', height: '8px', borderRadius: '4px', overflow: 'hidden', width: '100%' }}>
                      <div style={{ background: 'var(--color-burnt-sienna)', height: '100%', width: `${devopsScore}%`, opacity: 0.6, borderRadius: '4px' }} />
                    </div>
                  </div>

                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 'var(--text-sm)', marginBottom: '4px' }}>
                      <span style={{ fontWeight: 500 }}>Data Roles</span>
                      <span style={{ color: 'var(--text-secondary)', fontWeight: 500 }}>{dataScore}%</span>
                    </div>
                    <div style={{ background: 'var(--color-cork-shadow)', height: '8px', borderRadius: '4px', overflow: 'hidden', width: '100%' }}>
                      <div style={{ background: 'var(--color-burnt-sienna)', height: '100%', width: `${dataScore}%`, opacity: 0.4, borderRadius: '4px' }} />
                    </div>
                  </div>
                </div>

                {/* Top Missing Skills */}
                {missingSkillsToShow.length > 0 && (
                  <div style={{ borderTop: '1px dashed var(--color-cork-shadow)', paddingTop: 'var(--space-4)', marginTop: 'var(--space-2)' }}>
                    <h4 style={{ fontSize: '11px', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '8px' }}>
                      Top Missing Skills
                    </h4>
                    <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                      {missingSkillsToShow.map((skill: string) => (
                        <span 
                          key={skill} 
                          className="badge" 
                          style={{ 
                            borderColor: 'var(--color-burnt-sienna)', 
                            color: 'var(--color-burnt-sienna)',
                            fontSize: '10px',
                            padding: '3px 10px',
                            borderRadius: '12px'
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

            {/* Recommended Matching Jobs */}
            <div className="card" style={{ background: 'transparent' }}>
              <div className="card__header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <h3 style={{ fontSize: 'var(--text-lg)', fontWeight: 500, color: 'var(--text)', margin: 0 }}>Recommended Matching Jobs</h3>
                  <p style={{ fontSize: 'var(--text-xs)', color: 'var(--text-secondary)', marginTop: '2px', margin: 0 }}>Matching positions aligned with your skillset from active jobs.</p>
                </div>
                <Link to="/candidate/jobs" style={{ fontSize: '12px', color: 'var(--color-burnt-sienna)', textDecoration: 'underline' }}>Explore Feed &rarr;</Link>
              </div>
              <div className="card__body" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
                {recommendedJobs.length > 0 ? (
                  recommendedJobs.slice(0, 3).map((job) => (
                    <div key={job.id} style={{
                      border: '1px solid var(--color-cork-shadow)',
                      borderRadius: 'var(--radius-xl)',
                      padding: '16px',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      background: 'transparent'
                    }}>
                      <div>
                        <h4 style={{ fontSize: '15px', fontWeight: 500, color: 'var(--text)', margin: 0 }}>{job.title}</h4>
                        <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>{job.company_name} &bull; {job.department}</span>
                        <div style={{ marginTop: '8px', display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                          {(job.matching_skills || []).slice(0, 3).map((skill: string) => (
                            <span key={skill} className="chip">{skill}</span>
                          ))}
                        </div>
                      </div>
                      <div style={{ textAlign: 'right' }}>
                        <div style={{ fontSize: '18px', fontWeight: 600, color: 'var(--color-burnt-sienna)' }}>
                          {job.applicability_score}% Match
                        </div>
                        <Link to="/candidate/jobs" className="btn btn--secondary btn--sm" style={{ marginTop: '8px', padding: '4px 10px', borderRadius: '12px', border: '1px solid var(--color-warm-cream)', background: 'transparent', color: 'var(--text)' }}>
                          View &amp; Apply
                        </Link>
                      </div>
                    </div>
                  ))
                ) : (
                  <div style={{ textAlign: 'center', color: 'var(--text-secondary)', fontSize: '13px', padding: '24px 0' }}>
                    No job openings currently in feed. Check back later!
                  </div>
                )}
              </div>
            </div>

            {/* Upcoming Interviews Calendar Booking Widget */}
            <div className="card" style={{ background: 'transparent' }}>
              <div className="card__header">
                <h3 style={{ fontSize: 'var(--text-lg)', fontWeight: 500, color: 'var(--text)', margin: 0 }}>Upcoming Interviews &amp; Scheduling</h3>
                <p style={{ fontSize: 'var(--text-xs)', color: 'var(--text-secondary)', marginTop: '2px', margin: 0 }}>
                  Coordinate your live video screening calls and technical reviews.
                </p>
              </div>
              <div className="card__body" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
                {activeInterviews.length > 0 ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
                    {activeInterviews.map((iv) => (
                      <div 
                        key={iv.id}
                        style={{
                          border: '1px solid var(--color-cork-shadow)',
                          borderRadius: 'var(--radius-xl)',
                          padding: '16px',
                          background: 'transparent'
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                          <div>
                            <span className="badge" style={{ marginBottom: '8px', fontSize: '9px' }}>{iv.stage}</span>
                            <h4 style={{ fontSize: '16px', fontWeight: 500, color: 'var(--text)', margin: 0 }}>{iv.title}</h4>
                            <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '4px', margin: 0 }}>
                              🏢 {iv.company_name} &bull; 👤 {iv.interviewer_name}
                            </p>
                          </div>
                          <div style={{ textAlign: 'right' }}>
                            <span style={{ fontSize: '13px', fontWeight: 550, color: 'var(--color-burnt-sienna)' }}>
                              {new Date(iv.scheduled_at).toLocaleDateString([], { month: 'short', day: 'numeric' })} at {new Date(iv.scheduled_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                            </span>
                          </div>
                        </div>
                        {iv.video_link && (
                          <div style={{ marginTop: '12px', display: 'flex', gap: '8px' }}>
                            <a 
                              href={iv.video_link} 
                              target="_blank" 
                              rel="noreferrer" 
                              className="btn btn--primary btn--sm"
                              style={{ borderRadius: '12px' }}
                            >
                              Join Call
                            </a>
                            <Link to="/candidate/interviews" className="btn btn--secondary btn--sm" style={{ borderRadius: '12px' }}>
                              Reschedule
                            </Link>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <div 
                    style={{ 
                      border: '1px dashed var(--color-cork-shadow)',
                      borderRadius: 'var(--radius-xl)',
                      padding: 'var(--space-8) var(--space-4)',
                      textAlign: 'center',
                      color: 'var(--text-secondary)'
                    }}
                  >
                    📅 No upcoming interviews scheduled at this time. When a recruiter invites you to schedule, you will receive a scheduling link and booking options.
                  </div>
                )}
              </div>
            </div>

          </div>

          {/* Right Sidebar Column */}
          <div className="dashboard-sidebar" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)' }}>
            
            {/* Profile Completion Circular Conic Card */}
            <div className="card card__body" style={{ background: 'transparent' }}>
              <h3 style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Profile Completion
              </h3>
              
              <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-4)', marginTop: 'var(--space-4)' }}>
                {/* Conic circular progress indicator */}
                <div 
                  style={{ 
                    position: 'relative', 
                    width: '64px', 
                    height: '64px', 
                    borderRadius: '50%', 
                    background: `conic-gradient(var(--color-burnt-sienna) ${profileCompletion}%, var(--color-cork-shadow) 0)`,
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
                      background: 'var(--bg)', 
                      display: 'grid', 
                      placeItems: 'center',
                      fontSize: '13px',
                      fontWeight: 600,
                      color: 'var(--text)'
                    }}
                  >
                    {profileCompletion}%
                  </div>
                </div>

                <div>
                  <h4 style={{ fontSize: '14px', fontWeight: 500, color: 'var(--text)', margin: 0 }}>
                    {profileCompletion === 100 ? 'Profile Verified!' : 'Complete your setup'}
                  </h4>
                  <p style={{ fontSize: 'var(--text-xs)', color: 'var(--text-secondary)', marginTop: '4px', margin: 0, lineHeight: 1.3 }}>
                    {profileCompletion === 100 
                      ? 'Congratulations, you have unlocked 100% of your Career Hub capabilities!'
                      : 'Verify your phone number and load biography statement to hit 100% suitability matches.'
                    }
                  </p>
                </div>
              </div>
            </div>

            {/* Trust Badges */}
            <div className="card" style={{ background: 'transparent' }}>
              <div className="card__header" style={{ padding: 'var(--space-4)', borderBottom: '1px solid var(--color-cork-shadow)' }}>
                <h3 style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em', margin: 0 }}>
                  Verification Center
                </h3>
              </div>
              <div className="card__body" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)', padding: 'var(--space-4)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 'var(--text-sm)' }}>
                  <span>Email Verification</span>
                  {emailVerified ? (
                    <span className="badge badge--hire">Verified</span>
                  ) : (
                    <span className="badge badge--reject">Unverified</span>
                  )}
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 'var(--text-sm)' }}>
                  <span>Phone Verification</span>
                  {phoneVerified ? (
                    <span className="badge badge--hire">Verified</span>
                  ) : (
                    <span className="badge badge--interview">Unverified</span>
                  )}
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 'var(--text-sm)' }}>
                  <span>Identity Crypt</span>
                  <span className="badge badge--neutral">Unlinked</span>
                </div>
              </div>
            </div>

            {/* Quick Actions Panel */}
            <div className="card" style={{ background: 'transparent' }}>
              <div className="card__header" style={{ padding: 'var(--space-4)', borderBottom: '1px solid var(--color-cork-shadow)' }}>
                <h3 style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em', margin: 0 }}>
                  Quick Actions
                </h3>
              </div>
              <div className="card__body" style={{ display: 'flex', flexDirection: 'column', gap: '8px', padding: 'var(--space-4)' }}>
                <Link to="/candidate/resumes" className="btn btn--primary btn--sm btn--block" style={{ background: 'var(--color-dark-cork)', color: 'var(--text)', border: 'none', borderRadius: '12px' }}>
                  Upload New Resume (Max 3)
                </Link>
                <Link to="/candidate/profile" className="btn btn--secondary btn--sm btn--block" style={{ borderRadius: '12px' }}>
                  Verify Phone &amp; Email OTP
                </Link>
                <Link to="/candidate/jobs" className="btn btn--secondary btn--sm btn--block" style={{ borderRadius: '12px' }}>
                  Search Open Roles
                </Link>
              </div>
            </div>

            {/* Profile Statement Updates Form */}
            <form 
              id="bio-form"
              onSubmit={handleSaveBio}
              className="card" 
              style={{ background: 'transparent' }}
            >
              <div className="card__header" style={{ padding: 'var(--space-4)', borderBottom: '1px solid var(--color-cork-shadow)' }}>
                <h3 style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em', margin: 0 }}>
                  Professional Biography
                </h3>
              </div>
              <div className="card__body" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)', padding: 'var(--space-4)' }}>
                {bioSuccess && (
                  <div style={{ fontSize: '11px', color: 'var(--text)', border: '1px solid var(--color-warm-cream)', padding: '6px', borderRadius: '4px' }}>
                    ✅ Statement saved successfully!
                  </div>
                )}
                <div className="form-group" style={{ margin: 0 }}>
                  <label htmlFor="bio-textarea" style={{ fontSize: '9px', textTransform: 'uppercase', color: 'var(--text-secondary)' }}>
                    Career Bio Statement
                  </label>
                  <textarea
                    id="bio-textarea"
                    value={bioText}
                    onChange={(e) => setBioText(e.target.value)}
                    placeholder="Describe your technical background, specialties, and goals (e.g. Frontend Engineer specializing in single-page React apps)"
                    className="form-textarea"
                    style={{ 
                      minHeight: '80px', 
                      fontSize: '12.5px', 
                      marginTop: '4px',
                      background: 'transparent',
                      color: 'var(--text)',
                      border: 'none',
                      borderBottom: '1px solid var(--color-cork-shadow)'
                    }}
                    required
                  />
                </div>
                <button 
                  type="submit" 
                  className="btn btn--accent btn--sm"
                  style={{ alignSelf: 'flex-end', borderRadius: '12px', background: 'var(--color-dark-cork)', color: 'var(--text)', border: 'none', padding: '6px 14px' }}
                  disabled={submittingBio}
                >
                  {submittingBio ? 'Saving...' : 'Save Statement'}
                </button>
              </div>
            </form>

            {/* Resume Improvement Suggestions */}
            <div className="card" style={{ background: 'transparent' }}>
              <div className="card__header" style={{ padding: 'var(--space-4)', borderBottom: '1px solid var(--color-cork-shadow)' }}>
                <h3 style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em', margin: 0 }}>
                  Resume Diagnostics
                </h3>
              </div>
              <div className="card__body" style={{ display: 'flex', flexDirection: 'column', gap: '10px', padding: 'var(--space-4)', fontSize: '12px', lineHeight: 1.35 }}>
                <div style={{ color: 'var(--text)' }}>
                  💡 <strong style={{ color: 'var(--color-burnt-sienna)' }}>Boost DevOps Match:</strong> Mentioning <strong>Docker</strong> or <strong>Kubernetes</strong> on your resume could increase your DevOps alignment by 25%.
                </div>
                <div style={{ color: 'var(--text)' }}>
                  💡 <strong style={{ color: 'var(--color-burnt-sienna)' }}>Specify Frameworks:</strong> Ensure <strong>React</strong> and <strong>TypeScript</strong> are explicitly written in your core technical experience sections.
                </div>
                <div style={{ color: 'var(--text)' }}>
                  💡 <strong>Verification Boost:</strong> Fully verified candidates (Email + Phone SMS OTP) are highlighted to recruiters and experience 3x faster reviews.
                </div>
                <div style={{ color: 'var(--text)' }}>
                  💡 <strong>Target Roles:</strong> You can upload up to 3 separate CV documents to optimize matching for different pathways.
                </div>
              </div>
            </div>

          </div>
        </div>
      </div>
      <style>{`
        .booking-slot-btn:hover {
          border-color: var(--color-burnt-sienna) !important;
        }
      `}</style>
    </CandidateLayout>
  )
}
