interface JobPreviewSkillsProps {
  matchingSkills?: string[]
  missingSkills?: string[]
}

export default function JobPreviewSkills({ 
  matchingSkills = [], 
  missingSkills = [] 
}: JobPreviewSkillsProps) {
  if (matchingSkills.length === 0 && missingSkills.length === 0) return null

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
      <h4 style={{ fontSize: 'var(--text-sm)', fontWeight: 750, textTransform: 'uppercase', letterSpacing: '0.04em', color: 'var(--text-secondary)', margin: 0 }}>
        Skills Matching Audit
      </h4>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: 'var(--space-3)' }}>
        
        {/* Matching */}
        {matchingSkills.length > 0 && (
          <div style={{ border: '1px solid var(--border)', borderRadius: 'var(--radius-cards)', padding: 'var(--space-3)', background: 'var(--color-pure-white)' }}>
            <span style={{ fontSize: '11px', fontWeight: 750, color: 'var(--success)', display: 'block', marginBottom: '8px' }}>
              ✓ Matching Skills ({matchingSkills.length})
            </span>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
              {matchingSkills.map((skill, idx) => (
                <span 
                  key={idx} 
                  style={{ 
                    fontSize: '10px', 
                    padding: '2px 8px', 
                    borderRadius: '6px', 
                    background: 'var(--success-bg)', 
                    color: 'var(--success)',
                    fontWeight: 550
                  }}
                >
                  {skill}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Missing */}
        {missingSkills.length > 0 && (
          <div style={{ border: '1px solid var(--border)', borderRadius: 'var(--radius-cards)', padding: 'var(--space-3)', background: 'var(--color-pure-white)' }}>
            <span style={{ fontSize: '11px', fontWeight: 750, color: 'var(--text-secondary)', display: 'block', marginBottom: '8px' }}>
              ? Missing Skills ({missingSkills.length})
            </span>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
              {missingSkills.map((skill, idx) => (
                <span 
                  key={idx} 
                  style={{ 
                    fontSize: '10px', 
                    padding: '2px 8px', 
                    borderRadius: '6px', 
                    background: 'transparent', 
                    color: 'var(--text-secondary)',
                    border: '1px solid var(--color-cork-shadow)',
                    fontWeight: 400
                  }}
                >
                  {skill}
                </span>
              ))}
            </div>
          </div>
        )}

      </div>
    </div>
  )
}
