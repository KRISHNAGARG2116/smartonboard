import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

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

export interface ScreenAnalysis {
  score: number
  strengths: string[]
  concerns: string[]
  skills: string[]
  experience_years: string
  education: string
  recommendation: string
  summary: string
}

export interface ScreenResult {
  success: boolean
  analysis: ScreenAnalysis
  filename?: string
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

export const onboardEmployee = (data: OnboardRequest) =>
  api.post<OnboardResult>('/onboard', data).then(r => r.data)

export const screenResumeText = (data: { job_role: string; job_description?: string; resume_text: string }) =>
  api.post<ScreenResult>('/screen', data).then(r => r.data)

export const screenResumeFile = (formData: FormData) =>
  api.post<ScreenResult>('/screen/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }).then(r => r.data)

export const recruitCandidate = (formData: FormData) =>
  api.post<RecruitResult>('/recruit', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }).then(r => r.data)
