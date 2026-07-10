

interface PendingAction {
  id: string
  type: string  // draft_email, add_to_pool, move_stage
  details: string
}

interface AIActionCardProps {
  actions: PendingAction[]
  onAction: (id: string, approved: boolean) => void
}

export default function AIActionCard({ actions = [], onAction }: AIActionCardProps) {
  if (actions.length === 0) return null

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '12px',
        margin: '16px 0',
        fontFamily: 'var(--font-sans, sans-serif)'
      }}
    >
      <span
        style={{
          fontSize: '11px',
          fontWeight: 700,
          textTransform: 'uppercase',
          color: 'var(--text-secondary, #6b7280)',
          display: 'block',
          letterSpacing: '0.05em'
        }}
      >
        📥 Suggested Actions Queue
      </span>
      {actions.map((action) => (
        <div
          key={action.id}
          style={{
            background: 'var(--bg-card, #ffffff)',
            border: '1px solid var(--border, #e5e7eb)',
            borderRadius: '12px',
            padding: '16px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            boxShadow: 'var(--shadow-premium, 0 4px 20px -6px rgba(0,0,0,0.02))'
          }}
        >
          <div>
            <span
              style={{
                fontSize: '11px',
                fontWeight: 700,
                color: 'var(--accent, #3b82f6)',
                background: 'var(--accent-subtle, #eff6ff)',
                padding: '2px 8px',
                borderRadius: '4px',
                textTransform: 'uppercase'
              }}
            >
              {action.type.replace('_', ' ')}
            </span>
            <p style={{ margin: '8px 0 0 0', fontSize: '13px', color: 'var(--text-secondary)' }}>
              {action.details}
            </p>
          </div>
          <div style={{ display: 'flex', gap: '8px' }}>
            <button
              type="button"
              className="btn btn--danger"
              style={{
                fontSize: '12px',
                padding: '6px 12px',
                border: '1px solid #ef4444',
                color: '#ef4444',
                background: 'transparent',
                borderRadius: '6px',
                cursor: 'pointer'
              }}
              onClick={() => onAction(action.id, false)}
            >
              Reject
            </button>
            <button
              type="button"
              className="btn btn--primary"
              style={{
                fontSize: '12px',
                padding: '6px 12px',
                background: '#10b981',
                color: '#ffffff',
                border: 'none',
                borderRadius: '6px',
                cursor: 'pointer'
              }}
              onClick={() => onAction(action.id, true)}
            >
              Approve
            </button>
          </div>
        </div>
      ))}
    </div>
  )
}
