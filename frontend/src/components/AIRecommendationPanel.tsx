

interface AIRecommendationPanelProps {
  suggestions: string[]
  onSelectSuggestion: (suggestion: string) => void
}

export default function AIRecommendationPanel({
  suggestions = [],
  onSelectSuggestion
}: AIRecommendationPanelProps) {
  if (suggestions.length === 0) return null

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '10px',
        margin: '16px 0',
        padding: '16px',
        background: 'var(--accent-subtle, #eff6ff)',
        border: '1px solid #bfdbfe',
        borderRadius: '12px',
        fontFamily: 'var(--font-sans, sans-serif)'
      }}
    >
      <span
        style={{
          fontSize: '11px',
          fontWeight: 700,
          textTransform: 'uppercase',
          color: 'var(--accent, #3b82f6)',
          display: 'block',
          letterSpacing: '0.05em'
        }}
      >
        ✦ Suggested Next Steps
      </span>
      <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginTop: '6px' }}>
        {suggestions.map((suggestion) => (
          <button
            key={suggestion}
            type="button"
            style={{
              padding: '6px 12px',
              borderRadius: '20px',
              border: '1px solid #bfdbfe',
              background: '#ffffff',
              color: 'var(--text)',
              fontSize: '12px',
              fontWeight: 600,
              cursor: 'pointer',
              boxShadow: '0 2px 4px rgba(0,0,0,0.02)',
              transition: 'all 0.15s ease'
            }}
            onClick={() => onSelectSuggestion(suggestion)}
          >
            {suggestion}
          </button>
        ))}
      </div>
    </div>
  )
}
