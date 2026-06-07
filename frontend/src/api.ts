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
  company_id: string | null
}

export interface AuthResponse {
  access_token: string
  token_type: string
  user: User
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

export const fetchCompany = () => api.get<Company>('/v1/companies/me').then(r => r.data)

export const fetchJobs = (status?: string) =>
  api.get<Job[]>('/v1/jobs', { params: status ? { status } : {} }).then(r => r.data)

export const createJob = (data: {
  title: string
  department: string
  description: string
  status?: string
  start_date?: string | null
}) => api.post<Job>('/v1/jobs', data).then(r => r.data)

export const fetchApplications = (jobId?: string) =>
  api.get<Application[]>('/v1/applications', { params: jobId ? { job_id: jobId } : {} }).then(r => r.data)

export const createApplication = (data: {
  job_id: string
  candidate_name: string
  candidate_email: string
  candidate_phone?: string
  source?: string
}) => api.post<Application>('/v1/applications', data).then(r => r.data)

export const updateApplicationStatus = (id: string, status: string) =>
  api.patch<Application>(`/v1/applications/${id}`, { status }).then(r => r.data)

// --- Phase B Platform additions ---

export const fetchEmployees = () =>
  api.get<any[]>('/v1/employees').then(r => r.data)

export const fetchDlqRecords = () =>
  api.get<any[]>('/v1/employees/dlq').then(r => r.data)

export const fetchSyncMetrics = () =>
  api.get<any[]>('/v1/employees/metrics').then(r => r.data)

export const resolveTaskEscalation = (taskId: string, notes: string) =>
  api.post(`/v1/employees/tasks/${taskId}/escalations/resolve`, { resolution_notes: notes }).then(r => r.data)

export const retryDlqRecord = (id: string) =>
  api.post(`/v1/employees/dlq/${id}/retry`).then(r => r.data)

// --- Phase B Candidate Authentication ---

export const registerCandidate = (data: {
  email: string
  password: string
  full_name: string
}) => api.post<AuthResponse>('/v1/auth/register/candidate', data).then(r => r.data)

export const loginCandidate = (data: { email: string; password: string }) =>
  api.post<AuthResponse>('/v1/auth/login/candidate', data).then(r => r.data)

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




