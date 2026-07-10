

interface ToolCallStatus {
  node_id: string
  tool?: string
  status: 'running' | 'success' | 'failed' | 'pending'
  error?: string
  outcome?: string
}

interface ToolExecutionCardProps {
  statuses: ToolCallStatus[]
}

export default function ToolExecutionCard({ statuses = [] }: ToolExecutionCardProps) {
  if (statuses.length === 0) return null

  return (
    <div
      style={{
        background: 'var(--bg-subtle, #f9fafb)',
        border: '1px solid var(--border, #e5e7eb)',
        borderRadius: '12px',
        padding: '16px',
        margin: '12px 0',
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
          marginBottom: '12px',
          letterSpacing: '0.05em'
        }}
      >
        ⚙️ Agent Execution Timeline
      </span>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
        {statuses.map((step) => {
          const isSuccess = step.status === 'success'
          const isFailed = step.status === 'failed'
          const isRunning = step.status === 'running'

          let statusIcon = '○'
          let statusColor = '#9ca3af'
          if (isSuccess) {
            statusIcon = '✓'
            statusColor = '#10b981'
          } else if (isFailed) {
            statusIcon = '✗'
            statusColor = '#ef4444'
          } else if (isRunning) {
            statusIcon = '●'
            statusColor = 'var(--accent, #3b82f6)'
          }

          return (
            <div
              key={step.node_id}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                fontSize: '13px'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span
                  style={{
                    color: statusColor,
                    fontWeight: 800,
                    animation: isRunning ? 'pulse 1.5s infinite' : 'none'
                  }}
                >
                  {statusIcon}
                </span>
                <span style={{ fontWeight: 600, textTransform: 'capitalize' }}>
                  {step.tool ? step.tool.replace('_', ' ') : 'Conditional Check'}
                </span>
                {step.outcome && (
                  <span style={{ fontSize: '11px', color: 'var(--text-tertiary)', background: 'rgba(0,0,0,0.03)', padding: '1px 5px', borderRadius: '4px' }}>
                    {step.outcome}
                  </span>
                )}
              </div>
              <div style={{ fontSize: '12px', color: isFailed ? '#ef4444' : 'var(--text-secondary)' }}>
                {isRunning && <span className="shimmer">Processing...</span>}
                {isSuccess && 'Completed'}
                {isFailed && (step.error || 'Failed')}
              </div>
            </div>
          )
        })}
      </div>

      <style dangerouslySetInnerHTML={{ __html: `
        @keyframes pulse {
          0%, 100% { opacity: 0.4; }
          50% { opacity: 1; }
        }
      `}} />
    </div>
  )
}
