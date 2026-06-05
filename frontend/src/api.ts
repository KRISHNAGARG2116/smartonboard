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
  } | null
}

export const fetchCandidateMe = () => api.get<CandidateMeResponse>('/v1/auth/candidate/me').then(r => r.data.user)

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


