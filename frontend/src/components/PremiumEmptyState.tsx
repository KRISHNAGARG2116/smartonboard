
interface PremiumEmptyStateProps {
  icon?: string // emoji or SVG icon character
  title: string
  description: string
  actionLabel?: string
  onActionClick?: () => void
}

export default function PremiumEmptyState({
  icon = '📂',
  title,
  description,
  actionLabel,
  onActionClick
}: PremiumEmptyStateProps) {
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        textAlign: 'center',
        padding: '48px 24px',
        border: '1px dashed var(--border, #a3a6af)',
        borderRadius: '12px',
        background: 'var(--bg-subtle, #f7f7f8)',
        maxWidth: '540px',
        margin: '24px auto',
        gap: '16px',
        boxShadow: '0 2px 8px rgba(0, 0, 0, 0.02)'
      }}
    >
      <div style={{ fontSize: '40px', lineHeight: 1 }}>{icon}</div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        <h4 style={{ margin: 0, fontSize: '18px', fontWeight: 700, color: 'var(--text)' }}>
          {title}
        </h4>
        <p style={{ margin: 0, fontSize: '14px', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
          {description}
        </p>
      </div>
      {actionLabel && onActionClick && (
        <button
          type="button"
          onClick={onActionClick}
          className="btn btn--primary"
          style={{
            padding: '8px 18px',
            background: 'var(--text)',
            color: 'var(--surface)',
            border: 'none',
            borderRadius: '6px',
            fontWeight: 600,
            cursor: 'pointer',
            marginTop: '8px'
          }}
        >
          {actionLabel}
        </button>
      )}
    </div>
  )
}
