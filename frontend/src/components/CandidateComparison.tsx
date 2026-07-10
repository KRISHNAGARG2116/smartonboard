

interface CandidateDetail {
  id: string
  name: string
  email: string
  experience_years: string
  skills: string
  match_score: number
  score_bar: string
  strengths: string[]
  concerns: string[]
}

interface CandidateComparisonProps {
  candidates: CandidateDetail[]
}

export default function CandidateComparison({ candidates = [] }: CandidateComparisonProps) {
  if (candidates.length === 0) return null

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '20px',
        margin: '16px 0',
        fontFamily: 'var(--font-sans, sans-serif)',
        color: 'var(--text)'
      }}
    >
      <h4 style={{ margin: 0, fontSize: '15px', fontWeight: 700 }}>Candidate Comparison Matrix</h4>
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: `repeat(${candidates.length}, 1fr)`,
          gap: '16px',
          overflowX: 'auto'
        }}
      >
        {candidates.map((cand) => {
          const filledCount = Math.round(cand.match_score / 10)
          const barItems = Array.from({ length: 10 }, (_, i) => i < filledCount)

          return (
            <div
              key={cand.id}
              style={{
                background: 'var(--bg-card, #ffffff)',
                border: '1px solid var(--border, #e5e7eb)',
                borderRadius: '12px',
                padding: '20px',
                display: 'flex',
                flexDirection: 'column',
                gap: '16px',
                boxShadow: 'var(--shadow-premium, 0 4px 20px -6px rgba(0,0,0,0.02))'
              }}
            >
              <div>
                <h5 style={{ margin: 0, fontSize: '16px', fontWeight: 700 }}>{cand.name}</h5>
                <span style={{ fontSize: '12px', color: 'var(--text-tertiary)' }}>{cand.email}</span>
              </div>

              {/* Visual Score Percentage Bar */}
              <div>
                <span style={{ fontSize: '11px', color: 'var(--text-secondary)', fontWeight: 600, display: 'block', marginBottom: '6px' }}>
                  AI Fit Score
                </span>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <div style={{ display: 'flex', gap: '2px', background: '#f3f4f6', padding: '3px', borderRadius: '6px', flex: 1 }}>
                    {barItems.map((filled, idx) => (
                      <div
                        key={idx}
                        style={{
                          height: '8px',
                          flex: 1,
                          borderRadius: '2px',
                          background: filled
                            ? cand.match_score >= 90 ? '#10b981' : cand.match_score >= 75 ? '#3b82f6' : '#f59e0b'
                            : '#e5e7eb'
                        }}
                      />
                    ))}
                  </div>
                  <span style={{ fontSize: '13px', fontWeight: 700 }}>{cand.match_score}%</span>
                </div>
              </div>

              <div style={{ fontSize: '13px' }}>
                <strong>Experience:</strong> {cand.experience_years}
              </div>

              <div style={{ fontSize: '13px' }}>
                <strong>Key Skills:</strong>
                <p style={{ margin: '4px 0 0 0', color: 'var(--text-secondary)', fontSize: '12.5px' }}>
                  {cand.skills}
                </p>
              </div>

              {/* Strengths */}
              <div>
                <span style={{ fontSize: '12px', color: '#10b981', fontWeight: 700, display: 'block', marginBottom: '4px' }}>
                  ✓ Key Strengths
                </span>
                <ul style={{ margin: 0, paddingLeft: '16px', fontSize: '12.5px', color: 'var(--text-secondary)' }}>
                  {cand.strengths.map((s, idx) => (
                    <li key={idx}>{s}</li>
                  ))}
                </ul>
              </div>

              {/* Concerns */}
              {cand.concerns.length > 0 && (
                <div>
                  <span style={{ fontSize: '12px', color: '#f59e0b', fontWeight: 700, display: 'block', marginBottom: '4px' }}>
                    ⚠ Considerations
                  </span>
                  <ul style={{ margin: 0, paddingLeft: '16px', fontSize: '12.5px', color: 'var(--text-secondary)' }}>
                    {cand.concerns.map((c, idx) => (
                      <li key={idx}>{c}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
