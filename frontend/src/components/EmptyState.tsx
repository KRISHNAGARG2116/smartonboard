
import React from 'react'

interface EmptyStateProps {
  type: 'jobs' | 'applications' | 'interviews' | 'resumes' | 'analytics'
  title?: string
  description?: string
  actionLabel?: string
  onAction?: () => void
}

export default function EmptyState({
  type,
  title,
  description,
  actionLabel,
  onAction,
}: EmptyStateProps): React.ReactElement {
  const getIcon = () => {
    switch (type) {
      case 'jobs':
        return (
          <svg
            width="48"
            height="48"
            viewBox="0 0 24 24"
            fill="none"
            stroke="var(--color-burnt-sienna)"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <rect x="2" y="7" width="20" height="14" rx="2" ry="2" />
            <path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16" />
          </svg>
        )
      case 'applications':
        return (
          <svg
            width="48"
            height="48"
            viewBox="0 0 24 24"
            fill="none"
            stroke="var(--color-burnt-sienna)"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M22 2L11 13" />
            <path d="M22 2L15 22L11 13L2 9L22 2Z" />
          </svg>
        )
      case 'interviews':
        return (
          <svg
            width="48"
            height="48"
            viewBox="0 0 24 24"
            fill="none"
            stroke="var(--color-burnt-sienna)"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
            <line x1="16" y1="2" x2="16" y2="6" />
            <line x1="8" y1="2" x2="8" y2="6" />
            <line x1="3" y1="10" x2="21" y2="10" />
          </svg>
        )
      case 'resumes':
        return (
          <svg
            width="48"
            height="48"
            viewBox="0 0 24 24"
            fill="none"
            stroke="var(--color-burnt-sienna)"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <polyline points="14 2 14 8 20 8" />
            <line x1="16" y1="13" x2="8" y2="13" />
            <line x1="16" y1="17" x2="8" y2="17" />
            <polyline points="10 9 9 9 8 9" />
          </svg>
        )
      case 'analytics':
        return (
          <svg
            width="48"
            height="48"
            viewBox="0 0 24 24"
            fill="none"
            stroke="var(--color-burnt-sienna)"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <line x1="18" y1="20" x2="18" y2="10" />
            <line x1="12" y1="20" x2="12" y2="4" />
            <line x1="6" y1="20" x2="6" y2="14" />
          </svg>
        )
      default:
        return null
    }
  }

  const getDefaultTitle = () => {
    switch (type) {
      case 'jobs':
        return 'No active job openings'
      case 'applications':
        return 'No applications tracked'
      case 'interviews':
        return 'No interviews scheduled'
      case 'resumes':
        return 'No resumes uploaded'
      case 'analytics':
        return 'No sync metrics available'
    }
  }

  const getDefaultDescription = () => {
    switch (type) {
      case 'jobs':
        return 'Get started by creating your first job opening to recruit qualified candidates.'
      case 'applications':
        return 'Candidates have not submitted applications yet. Apply to jobs or import resumes to trigger matching.'
      case 'interviews':
        return 'Coordinated screenings and live technical evaluations will show up here once scheduled.'
      case 'resumes':
        return 'Upload up to 3 resumes to let the AI screen your profile against active job specifications.'
      case 'analytics':
        return 'Connect to Gusto, BambooHR, or trigger an outbox sweep pipeline to sync organizational statistics.'
    }
  }

  return (
    <div
      className="empty-state"
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        textAlign: 'center',
        padding: 'var(--space-12) var(--space-6)',
        border: '1px dashed var(--color-cork-shadow)',
        borderRadius: 'var(--radius-cards)',
        background: 'transparent',
        margin: 'var(--space-4) 0'
      }}
    >
      <div style={{ marginBottom: 'var(--space-4)' }}>{getIcon()}</div>
      <h3
        style={{
          fontSize: '18px',
          fontWeight: 500,
          marginBottom: 'var(--space-2)',
          color: 'var(--text)'
        }}
      >
        {title || getDefaultTitle()}
      </h3>
      <p
        style={{
          fontSize: '14px',
          color: 'var(--text-secondary)',
          maxWidth: '360px',
          margin: '0 auto var(--space-5) auto',
          lineHeight: '1.4'
        }}
      >
        {description || getDefaultDescription()}
      </p>
      {actionLabel && onAction && (
        <button
          type="button"
          className="btn btn--primary"
          onClick={onAction}
          style={{
            borderRadius: 'var(--radius-buttons-pill)',
            padding: '10px 20px',
            fontSize: '12px'
          }}
        >
          {actionLabel}
        </button>
      )}
    </div>
  )
}
