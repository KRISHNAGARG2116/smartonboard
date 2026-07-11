import axios from 'axios'

const TOKEN_KEY = 'smartonboard_token'

export const api = axios.create({ baseURL: '/api' })

api.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY)
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

let isRefreshing = false
let failedQueue: any[] = []

const processQueue = (error: any, token: string | null = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error)
    } else {
      prom.resolve(token)
    }
  })
  failedQueue = []
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config
    if (
      error.response?.status === 401 &&
      !originalRequest._retry &&
      !originalRequest.url?.includes('/auth/login') &&
      !originalRequest.url?.includes('/auth/register') &&
      !originalRequest.url?.includes('/auth/refresh')
    ) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject })
        })
          .then((token) => {
            originalRequest.headers.Authorization = `Bearer ${token}`
            return api(originalRequest)
          })
          .catch((err) => Promise.reject(err))
      }

      originalRequest._retry = true
      isRefreshing = true

      try {
        const res = await api.post<{ access_token: string }>('/v1/auth/refresh')
        const { access_token } = res.data
        setAuthToken(access_token)
        api.defaults.headers.common['Authorization'] = `Bearer ${access_token}`
        originalRequest.headers.Authorization = `Bearer ${access_token}`
        processQueue(null, access_token)
        return api(originalRequest)
      } catch (refreshError) {
        processQueue(refreshError, null)
        setAuthToken(null)
        window.dispatchEvent(new Event('auth_session_expired'))
        return Promise.reject(refreshError)
      } finally {
        isRefreshing = false
      }
    }
    return Promise.reject(error)
  }
)

export function setAuthToken(token: string | null) {
  if (token) {
    localStorage.setItem(TOKEN_KEY, token)
  } else {
    localStorage.removeItem(TOKEN_KEY)
  }
}

export function getAuthToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

// --- Legacy AI types ---

export interface OnboardRequest {
  name: string
  role: string
  department: string
  start_date: string
  email: string
}

export interface OnboardResult {
  success: boolean
  employee_name: string
  role: string
  department: string
  documents_generated: string[]
  training_plan: string
  email_draft: string
  qa_context: string
}

export interface RecruitResult {
  success: boolean
  candidate: CandidateData
  screening: {
    matches: string[]
    gaps: string[]
    experience_match: boolean
    education_match: boolean
    skills_match_percentage: number
    screening_notes: string
  }
  scoring: ScoringResult
  decision: DecisionResult
  communication: CommunicationResult
  onboarding?: {
    documents_generated: string[]
    training_plan: string
    email_draft: string
  }
}

export interface CandidateData {
  name: string
  email: string
  phone: string
  skills: string[]
  experience_years: number
  education: string
  previous_roles: string[]
  summary: string
}

export interface ScoringResult {
  total_score: number
  skills_score: number
  experience_score: number
  education_score: number
  overall_fit: string
  strengths: string[]
  weaknesses: string[]
  scoring_reasoning: string
}

export interface DecisionResult {
  decision: 'HIRE' | 'INTERVIEW' | 'REJECT'
  confidence: string
  decision_reasoning: string
  suggested_interview_questions: string[]
  salary_recommendation: string
  flag_for_human_review: boolean
  flag_reason: string
}

export interface CommunicationResult {
  email_type: string
  email_content: string
  recipient: string
}

export const recruitCandidate = (formData: FormData) =>
  api.post<RecruitResult>('/recruit', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }).then(r => r.data)

// --- Phase 1A platform types ---

export interface User {
  id: string
  email: string
  full_name: string
  role: string
  email_verified: boolean
  phone_verified: boolean
  company_id: string | null
  company_verified?: boolean
  company_onboarding_completed?: boolean
}

export interface AuthResponse {
  access_token?: string
  token_type?: string
  user: User
  verification_required?: boolean
}

export interface Company {
  id: string
  name: string
  slug: string
  status: string
  domain_verified?: boolean
  created_at: string
}

export interface Job {
  id: string
  company_id: string
  title: string
  department: string
  description: string
  status: string
  start_date: string | null
  created_at: string
  updated_at: string
  settings?: any
}

export interface Application {
  id: string
  company_id: string
  job_id: string
  candidate_id: string
  status: string
  source: string
  created_at: string
  updated_at: string
  match_score?: number | null
  candidate?: { id: string; full_name: string; email: string; phone: string | null }
  job?: { id: string; title: string; department: string }
  current_stage_id?: string | null
  owner_id?: string | null
}

export const register = (data: {
  company_name: string
  email: string
  password: string
  full_name: string
}) => api.post<AuthResponse>('/v1/auth/register', data).then(r => r.data)

export const login = (data: { email: string; password: string }) =>
  api.post<AuthResponse>('/v1/auth/login', data).then(r => r.data)

export const fetchMe = () => api.get<User>('/v1/auth/me').then(r => r.data)

export const loginWithGoogle = (data: { credential: string; role: string }) =>
  api.post<AuthResponse>('/v1/auth/google', data).then(r => r.data)

export const setupCompany = (data: {
  company_name: string
  company_website: string
  company_domain: string
  industry: string
  company_size: string
}) => api.post<AuthResponse>('/v1/auth/setup-company', data).then(r => r.data)

export const fetchCompany = () => api.get<Company>('/v1/companies/me').then(r => r.data)

export const fetchJobs = (status?: string) =>
  api.get<Job[]>('/v1/jobs', { params: status ? { status } : {} }).then(r => r.data)

export const createJob = (data: {
  title: string
  department: string
  description: string
  status?: string
  start_date?: string | null
  settings?: any
}) => api.post<Job>('/v1/jobs', data).then(r => r.data)

export const updateJob = (jobId: string, data: {
  title?: string
  department?: string
  description?: string
  status?: string
  start_date?: string | null
  settings?: any
  client_updated_at?: string
  change_reason?: string
}) => api.patch<Job>(`/v1/jobs/${jobId}`, data).then(r => r.data)


export const fetchApplications = (jobId?: string) =>
  api.get<Application[]>('/v1/applications', { params: jobId ? { job_id: jobId } : {} }).then(r => r.data)

export const fetchInterviews = (applicationId: string) =>
  api.get<any[]>(`/v1/applications/${applicationId}/interviews`).then(r => r.data)

export const createInterview = (applicationId: string, data: {
  interviewer_id: string
  title: string
  stage: string
  scheduled_at: string
  duration_minutes: number
  video_link?: string | null
}) => api.post<any>(`/v1/applications/${applicationId}/interviews`, data).then(r => r.data)

export const updateInterview = (applicationId: string, interviewId: string, data: {
  interviewer_id?: string
  title?: string
  stage?: string
  scheduled_at?: string
  duration_minutes?: number
  video_link?: string | null
  is_cancelled?: boolean
}) => api.patch<any>(`/v1/applications/${applicationId}/interviews/${interviewId}`, data).then(r => r.data)

export const fetchFunnelAnalytics = (jobId?: string) =>
  api.get<any>('/v1/analytics/funnel', { params: jobId ? { job_id: jobId } : {} }).then(r => r.data)

export const fetchVelocityAnalytics = (jobId?: string) =>
  api.get<any>('/v1/analytics/velocity', { params: jobId ? { job_id: jobId } : {} }).then(r => r.data)


export const createApplication = (data: {
  job_id: string
  candidate_name: string
  candidate_email: string
  candidate_phone?: string
  source?: string
}) => api.post<Application>('/v1/applications', data).then(r => r.data)

export const updateApplicationStatus = (id: string, status: string) =>
  api.patch<Application>(`/v1/applications/${id}`, { status }).then(r => r.data)

export const fetchJobStages = (jobId: string) =>
  api.get<any[]>(`/v1/pipelines/${jobId}`).then(r => r.data)

export const moveApplicationStage = (applicationId: string, data: { target_stage_id: string, client_updated_at?: string }) =>
  api.post<Application>(`/v1/applications/${applicationId}/move-stage`, data).then(r => r.data)

export const assignApplicationOwner = (applicationId: string, data: { owner_id: string | null, client_updated_at?: string }) =>
  api.post<Application>(`/v1/applications/${applicationId}/assign`, data).then(r => r.data)

export const fetchApplicationTimeline = (applicationId: string, page?: number, pageSize?: number) =>
  api.get<any[]>(`/v1/applications/${applicationId}/timeline`, { params: { page, page_size: pageSize } }).then(r => r.data)

export const fetchDashboardSummary = () =>
  api.get<any>('/v1/dashboard/summary').then(r => r.data)

// --- Phase B Platform additions ---

export const fetchEmployees = () =>
  api.get<any[]>('/v1/employees').then(r => r.data)


export const resolveTaskEscalation = (taskId: string, notes: string) =>
  api.post(`/v1/employees/tasks/${taskId}/escalations/resolve`, { resolution_notes: notes }).then(r => r.data)

export const retryDlqRecord = (id: string) =>
  api.post(`/v1/employees/dlq/${id}/retry`).then(r => r.data)

// --- Phase B Candidate Authentication ---

export const registerCandidate = (data: {
  email: string
  password: string
  full_name: string
  phone_number: string
}) => api.post<AuthResponse>('/v1/auth/register/candidate', data).then(r => r.data)

export const loginCandidate = (data: { email: string; password: string }) =>
  api.post<AuthResponse>('/v1/auth/login/candidate', data).then(r => r.data)

export const sendPhoneOTP = (email: string, phoneNumber: string) =>
  api.post<{ success: boolean; message: string }>('/v1/auth/phone/send-otp', { email, phone_number: phoneNumber }).then(r => r.data)

export const verifyPhoneOTP = (email: string, code: string) =>
  api.post<AuthResponse>('/v1/auth/phone/verify-otp', { email, code }).then(r => r.data)

export const verifyEmailOTP = (email: string, code: string) =>
  api.post<AuthResponse>('/v1/auth/email/verify-otp', { email, code }).then(r => r.data)

export const getVerificationStatus = (email: string) =>
  api.get<{ email_verified: boolean; phone_verified: boolean; verification_required: boolean; phone_number: string | null }>(
    `/v1/auth/verification-status?email=${encodeURIComponent(email)}`
  ).then(r => r.data)

export interface CandidateMeResponse {
  user: User
  profile: {
    id: string
    full_name: string
    phone_number: string | null
    phone_verified: boolean
    email_verified: boolean
    location: string | null
    profile_status: string | null
    summary: string | null
  } | null
}

export const fetchCandidateMe = () => api.get<CandidateMeResponse>('/v1/auth/candidate/me').then(r => r.data.user)

export const fetchCandidateProfile = () => api.get<CandidateMeResponse>('/v1/auth/candidate/me').then(r => r.data)

export const updateCandidateProfile = (data: { full_name: string; phone_number?: string; location?: string; summary?: string | null }) =>
  api.put<CandidateMeResponse>('/v1/auth/candidate/profile', data).then(r => r.data)

export const sendCandidateEmailOtp = (email: string) =>
  api.post('/v1/auth/candidate/email/send-otp', { email }).then(r => r.data)

export const verifyCandidateEmailOtp = (email: string, code: string) =>
  api.post('/v1/auth/candidate/email/verify-otp', { email, code }).then(r => r.data)

export const sendCandidatePhoneOtp = (phoneNumber: string) =>
  api.post('/v1/auth/candidate/phone/send-otp', { phone_number: phoneNumber }).then(r => r.data)

export const verifyCandidatePhoneOtp = (phoneNumber: string, code: string) =>
  api.post('/v1/auth/candidate/phone/verify-otp', { phone_number: phoneNumber, code }).then(r => r.data)

export interface CandidateResume {
  id: string
  filename: string
  file_path: string
  is_active: boolean
  parsed_skills: string[]
  parsed_summary: string
  created_at: string
}

export const fetchCandidateResumes = () =>
  api.get<CandidateResume[]>('/v1/auth/candidate/resumes').then(r => r.data)

export const uploadCandidateResume = (formData: FormData) =>
  api.post<{ task_id: string; quarantine_file_id: string; status: string }>('/v1/auth/candidate/resumes/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  }).then(r => r.data)

export const toggleCandidateResumeActive = (resumeId: string) =>
  api.post<{ success: boolean; message: string }>(`/v1/auth/candidate/resumes/${resumeId}/toggle-active`).then(r => r.data)

export const deleteCandidateResume = (resumeId: string) =>
  api.delete<{ success: boolean; message: string }>(`/v1/auth/candidate/resumes/${resumeId}`).then(r => r.data)

// --- Phase E Job Feed & Applications ---

export interface JobFeedItem {
  id: string
  company_id: string
  company_name: string
  title: string
  department: string
  description: string
  status: string
  start_date: string | null
  applicability_score: number
  matching_skills: string[]
  missing_skills: string[]
  settings?: any
}

export interface JobFeedResponse {
  total: number
  page: number
  limit: number
  results: JobFeedItem[]
}

export interface ApplyResponse {
  success: boolean
  application_id: string
  status: string
}

export const fetchJobFeed = (page = 1, limit = 10) =>
  api.get<JobFeedResponse>('/v1/jobs/feed', { params: { page, limit } }).then(r => r.data)

export const applyToJob = (jobId: string, resumeId: string) =>
  api.post<ApplyResponse>('/v1/applications/apply', { job_id: jobId, resume_id: resumeId }).then(r => r.data)

// --- Phase F Applications & Interviews ---

export interface ApplicationSnapshotData {
  id: string
  resume_snapshot: {
    id: string
    filename: string
    file_path: string
    parsed_skills: string[]
    parsed_summary: string
    created_at: string
  }
  candidate_snapshot: {
    full_name: string
    email: string
    phone_number: string | null
    location: string | null
    skills: string[]
    summary: string
  }
  created_at: string
}

export interface CandidateApplicationItem {
  id: string
  company_id: string
  company_name: string
  job_id: string
  job_title: string
  job_department: string
  status: string
  created_at: string
  updated_at: string
  snapshot: ApplicationSnapshotData | null
}

export interface CandidateInterviewSlot {
  id: string
  start_time: string
  end_time: string
  status: string
}

export interface CandidateInterviewItem {
  id: string
  title: string
  stage: string
  scheduled_at: string
  duration_minutes: number
  video_link: string | null
  is_cancelled: boolean
  company_name: string
  job_title: string
  interviewer_name: string
  slot: CandidateInterviewSlot | null
}

export const fetchMyApplications = () =>
  api.get<CandidateApplicationItem[]>('/v1/applications/me').then(r => r.data)

export const withdrawApplication = (applicationId: string) =>
  api.post<{ success: boolean; message: string; notification_draft: any }>(`/v1/applications/${applicationId}/withdraw`).then(r => r.data)

export const fetchMyInterviews = () =>
  api.get<CandidateInterviewItem[]>('/v1/candidate/interviews').then(r => r.data)

export const cancelCandidateBooking = (slotId: string) =>
  api.post<{ status: string; message: string }>(`/v1/candidate/bookings/${slotId}/cancel`).then(r => r.data)

export const rescheduleCandidateBooking = (slotId: string, newStartTime: string) =>
  api.post<{ status: string; slot_id: string; start_time: string; end_time: string }>(
    `/v1/candidate/bookings/${slotId}/reschedule`,
    { new_start_time: newStartTime }
  ).then(r => r.data)

export const fetchJob = (jobId: string) =>
  api.get<any>(`/v1/jobs/${jobId}`).then(r => r.data)

export const fetchCompanyUsers = () =>
  api.get<User[]>(`/v1/companies/me/users`).then(r => r.data)


// --- Phase B.2 AI & Intelligent ATS Builder Helpers ---

export interface JobDescriptionGenerateRequest {
  title: string
  department: string
  industry?: string | null
  workplace_type?: string | null
  employment_type?: string | null
  seniority?: string | null
  required_skills?: string[] | null
  preferred_skills?: string[] | null
  section?: string | null
}

export interface JobDescriptionGenerateResponse {
  success: boolean
  error_code?: string | null
  message?: string | null
  retryable?: boolean | null
  description?: string | null
  responsibilities?: string | null
  requirements?: string | null
  benefits?: string | null
  qualifications?: string | null
}

export interface SkillSuggestionsRequest {
  title: string
  department?: string | null
  existing_skills?: string[] | null
}

export interface SkillSuggestionsResponse {
  required_skills: string[]
  preferred_skills: string[]
  technologies: string[]
  languages: string[]
}

export interface JobQualityAnalyzeRequest {
  title: string
  department: string
  description: string
  settings?: any
}

export interface JobQualityAnalyzeResponse {
  score: number
  warnings: string[]
  recommendations: string[]
}

export interface JobRevision {
  id: string
  version: number
  title: string
  department: string
  job_status: string
  change_reason?: string | null
  created_by?: string | null
  created_at: string
}

export interface JobRevisionDetail extends JobRevision {
  job_id: string
  description: string
  settings?: any
}

export const generateJobDescription = (
  data: JobDescriptionGenerateRequest,
  options?: { signal?: AbortSignal; idempotencyKey?: string }
) => {
  const headers: Record<string, string> = {}
  if (options?.idempotencyKey) {
    headers['Idempotency-Key'] = options.idempotencyKey
  }
  return api.post<JobDescriptionGenerateResponse>('/v1/jobs/generate-description', data, {
    signal: options?.signal,
    headers,
  }).then(r => r.data)
}

export const suggestSkills = (data: SkillSuggestionsRequest) =>
  api.post<SkillSuggestionsResponse>('/v1/jobs/suggest-skills', data).then(r => r.data)

export const analyzeJobQuality = (data: JobQualityAnalyzeRequest) =>
  api.post<JobQualityAnalyzeResponse>('/v1/jobs/analyze-quality', data).then(r => r.data)

export const fetchJobRevisions = (jobId: string) =>
  api.get<JobRevision[]>(`/v1/jobs/${jobId}/revisions`).then(r => r.data)

export const fetchJobRevisionDetail = (jobId: string, version: number) =>
  api.get<JobRevisionDetail>(`/v1/jobs/${jobId}/revisions/${version}`).then(r => r.data)





