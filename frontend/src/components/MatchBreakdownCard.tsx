import MatchScoreBadge from './MatchScoreBadge'

interface MatchBreakdownCardProps {
  score: number
  strengths: string[]
  roleConsiderations: string[]
  summaryText?: string
}

export default function MatchBreakdownCard({
  score,
  strengths = [],
  roleConsiderations = [],
  summaryText
}: MatchBreakdownCardProps) {
  return (
    <div
      style={{
        background: 'var(--bg-card, #ffffff)',
        border: '1px solid var(--border, #e5e7eb)',
        borderRadius: '16px',
        padding: '24px',
        boxShadow: 'var(--shadow-premium, 0 10px 30px -10px rgba(0,0,0,0.04))',
        fontFamily: 'var(--font-sans, sans-serif)',
        display: 'flex',
        flexDirection: 'column',
        gap: '20px',
        maxWidth: '440px'
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
        <MatchScoreBadge score={score} size={64} strokeWidth={5} />
        <div>
          <h3 style={{ fontSize: '18px', fontWeight: 700, margin: 0, color: 'var(--text)' }}>
            Your Match Estimate
          </h3>
          <p style={{ fontSize: '13px', color: 'var(--text-secondary)', margin: '4px 0 0 0' }}>
            AI-assisted alignment breakdown
          </p>
        </div>
      </div>

      {summaryText && (
        <p style={{ fontSize: '14px', lineHeight: 1.6, color: 'var(--text-secondary)', margin: 0 }}>
          {summaryText}
        </p>
      )}

      {/* Strengths */}
      {strengths.length > 0 && (
        <div>
          <h4 style={{ fontSize: '14px', fontWeight: 650, margin: '0 0 8px 0', color: '#10b981' }}>
            ✦ Strengths & Alignment
          </h4>
          <ul style={{ margin: 0, paddingLeft: '20px', fontSize: '13.5px', color: 'var(--text)', display: 'flex', flexDirection: 'column', gap: '6px' }}>
            {strengths.map((str, idx) => (
              <li key={idx}>{str}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Role Considerations */}
      {roleConsiderations.length > 0 && (
        <div>
          <h4 style={{ fontSize: '14px', fontWeight: 650, margin: '0 0 8px 0', color: '#f59e0b' }}>
            ✦ Role Considerations
          </h4>
          <ul style={{ margin: 0, paddingLeft: '20px', fontSize: '13.5px', color: 'var(--text)', display: 'flex', flexDirection: 'column', gap: '6px' }}>
            {roleConsiderations.map((con, idx) => (
              <li key={idx}>{con}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Mandatory Advisory Disclaimer */}
      <div
        style={{
          borderTop: '1px solid var(--border-subtle, #f3f4f6)',
          paddingTop: '16px',
          marginTop: '4px'
        }}
      >
        <span
          style={{
            fontSize: '11px',
            lineHeight: 1.5,
            color: 'var(--text-tertiary, #9ca3af)',
            display: 'block',
            fontStyle: 'italic'
          }}
        >
          Match is an AI-assisted estimate based on your profile and this job. Recruiters make the final hiring decisions.
        </span>
      </div>
    </div>
  )
}
