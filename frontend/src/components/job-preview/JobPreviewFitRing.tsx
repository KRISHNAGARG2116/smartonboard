interface JobPreviewFitRingProps {
  applicabilityScore?: number
  matchingSkillsCount: number
  totalSkillsCount: number
}

export default function JobPreviewFitRing({ 
  applicabilityScore = 100, 
  matchingSkillsCount, 
  totalSkillsCount 
}: JobPreviewFitRingProps) {
  const displayScore = totalSkillsCount === 0 ? 100 : applicabilityScore

  return (
    <div 
      style={{ 
        display: 'flex', 
        alignItems: 'center', 
        gap: 'var(--space-5)', 
        padding: 'var(--space-4)', 
        background: 'var(--color-pure-white)', 
        borderRadius: 'var(--radius-cards)', 
        border: '1px solid var(--border)' 
      }}
    >
      <div 
        style={{
          position: 'relative',
          width: '60px',
          height: '60px',
          borderRadius: '50%',
          background: `conic-gradient(var(--color-rust) ${displayScore}%, var(--color-cork-shadow) 0)`,
          display: 'grid',
          placeItems: 'center',
          flexShrink: 0
        }}
      >
        <div 
          style={{
            position: 'absolute',
            inset: '5px',
            borderRadius: '50%',
            background: 'var(--color-pure-white)',
            display: 'grid',
            placeItems: 'center',
            fontSize: 'var(--text-sm)',
            fontWeight: 800
          }}
        >
          {displayScore}%
        </div>
      </div>
      
      <div>
        <h4 style={{ fontSize: 'var(--text-sm)', fontWeight: 750, margin: 0 }}>Personalized Applicability Fit</h4>
        <p style={{ fontSize: 'var(--text-xs)', color: 'var(--text-secondary)', marginTop: '2px', margin: 0, lineHeight: 1.3 }}>
          {totalSkillsCount === 0 ? (
            'This job has no specific skills configuration. All candidates match at 100%.'
          ) : (
            `Your resume matches ${matchingSkillsCount} of ${totalSkillsCount} identified requirements.`
          )}
        </p>
      </div>
    </div>
  )
}
