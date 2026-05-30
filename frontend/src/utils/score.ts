export function scoreTier(score: number): 'high' | 'mid' | 'low' {
  if (score >= 80) return 'high'
  if (score >= 60) return 'mid'
  return 'low'
}

export function scoreClass(score: number): string {
  return `score--${scoreTier(score)}`
}

export type Decision = 'HIRE' | 'INTERVIEW' | 'REJECT'

export function decisionBadge(decision: string): {
  className: string
  label: string
} {
  if (decision === 'HIRE') return { className: 'badge--hire', label: 'Hire' }
  if (decision === 'INTERVIEW') return { className: 'badge--interview', label: 'Interview' }
  return { className: 'badge--reject', label: 'Reject' }
}
