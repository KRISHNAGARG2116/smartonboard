

interface MatchScoreBadgeProps {
  score: number | null | undefined
  size?: number
  strokeWidth?: number
}

export default function MatchScoreBadge({
  score,
  size = 48,
  strokeWidth = 4
}: MatchScoreBadgeProps) {
  const isLoading = score === null || score === undefined

  // Color mapping according to specifications:
  // 90-100: Green, 75-89: Blue, 60-74: Amber, Below 60: Gray. No red!
  const getBadgeColor = (val: number) => {
    if (val >= 90) return '#10b981' // Green
    if (val >= 75) return '#3b82f6' // Blue
    if (val >= 60) return '#f59e0b' // Amber
    return '#6b7280' // Gray
  }

  const color = isLoading ? '#e5e7eb' : getBadgeColor(score)
  const radius = (size - strokeWidth) / 2
  const circumference = radius * 2 * Math.PI
  const offset = isLoading ? circumference : circumference - (score / 100) * circumference

  return (
    <div
      style={{
        position: 'relative',
        width: `${size}px`,
        height: `${size}px`,
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontFamily: 'var(--font-sans, sans-serif)',
      }}
    >
      {isLoading ? (
        // Premium Shimmer state representing "○•••" loading
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '11px',
            fontWeight: 700,
            color: 'var(--text-tertiary)',
            animation: 'pulse 1.5s infinite ease-in-out',
            letterSpacing: '0.1em'
          }}
        >
          ○•••
        </div>
      ) : (
        <span
          style={{
            position: 'absolute',
            fontSize: size > 40 ? '13px' : '10px',
            fontWeight: 700,
            color: color,
            textAlign: 'center'
          }}
        >
          {score}%
        </span>
      )}

      <svg
        width={size}
        height={size}
        style={{
          transform: 'rotate(-90deg)',
          animation: isLoading ? 'spin 2s linear infinite' : 'none'
        }}
      >
        {/* Background Track */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="transparent"
          stroke="var(--border-subtle, rgba(0,0,0,0.06))"
          strokeWidth={strokeWidth}
        />
        {/* Indicator Track */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="transparent"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          style={{
            transition: 'stroke-dashoffset 0.8s cubic-bezier(0.4, 0, 0.2, 1), stroke 0.4s'
          }}
        />
      </svg>

      <style dangerouslySetInnerHTML={{ __html: `
        @keyframes pulse {
          0%, 100% { opacity: 0.4; }
          50% { opacity: 0.9; }
        }
        @keyframes spin {
          100% { transform: rotate(270deg); }
        }
      `}} />
    </div>
  )
}
