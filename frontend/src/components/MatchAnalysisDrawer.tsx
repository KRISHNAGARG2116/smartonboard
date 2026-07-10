import { useState } from 'react'
import MatchScoreBadge from './MatchScoreBadge'

interface MatchAnalysisDrawerProps {
  candidateId: string
  jobId: string
  score: number
  confidence: string
  confidenceExplanation: string[]
  breakdown: {
    skills: number
    experience: number
    industry: number
    location: number
    education: number
    role_alignment: number
  }
  recruiterAnalysis: {
    strengths?: string[]
    considerations?: string[]
    placement_advice?: string
  }
  onSubmitFeedback: (rating: 'helpful' | 'not_helpful', reason?: string) => Promise<void>
}

export default function MatchAnalysisDrawer({
  candidateId,
  jobId,
  score,
  confidence,
  confidenceExplanation = [],
  breakdown,
  recruiterAnalysis,
  onSubmitFeedback
}: MatchAnalysisDrawerProps) {
  const [feedbackSubmitted, setFeedbackSubmitted] = useState(false)
  const [rating, setRating] = useState<'helpful' | 'not_helpful' | null>(null)
  const [selectedReason, setSelectedReason] = useState<string>('')
  const [loading, setLoading] = useState(false)

  const handleRatingClick = (type: 'helpful' | 'not_helpful') => {
    setRating(type)
  }

  const submitFeedback = async () => {
    if (!rating) return
    setLoading(true)
    try {
      console.log(`Match score review feedback: Candidate ${candidateId}, Job ${jobId}`)
      await onSubmitFeedback(rating, selectedReason || undefined)
      setFeedbackSubmitted(true)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const feedbackReasons = [
    'Very Accurate',
    'Mostly Accurate',
    'Missed Skills',
    'Wrong Experience',
    'Wrong Industry',
    'Other'
  ]

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '24px',
        padding: '16px',
        fontFamily: 'var(--font-sans, sans-serif)',
        color: 'var(--text)'
      }}
    >
      {/* Header Summary */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '20px',
          background: 'var(--color-fog, #f9fafb)',
          padding: '16px',
          borderRadius: '12px',
          border: '1px solid var(--border, #e5e7eb)'
        }}
      >
        <MatchScoreBadge score={score} size={72} strokeWidth={6} />
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <h4 style={{ margin: 0, fontSize: '18px', fontWeight: 700 }}>AI Match Analysis</h4>
            <span
              className={`badge badge--${confidence === 'high' ? 'success' : confidence === 'medium' ? 'info' : 'secondary'}`}
              style={{
                fontSize: '11px',
                padding: '2px 8px',
                borderRadius: '999px',
                textTransform: 'uppercase',
                fontWeight: 700,
                background: confidence === 'high' ? '#d1fae5' : confidence === 'medium' ? '#dbeafe' : '#f3f4f6',
                color: confidence === 'high' ? '#065f46' : confidence === 'medium' ? '#1e40af' : '#374151'
              }}
            >
              {confidence} Confidence
            </span>
          </div>
          <div style={{ marginTop: '6px', display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
            {confidenceExplanation.map((reason, idx) => (
              <span key={idx} style={{ fontSize: '11px', color: 'var(--text-secondary)', background: 'rgba(0,0,0,0.03)', padding: '2px 6px', borderRadius: '4px' }}>
                ✓ {reason}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Component Scores Breakdown */}
      <div>
        <h5 style={{ margin: '0 0 12px 0', fontSize: '14px', fontWeight: 650, textTransform: 'uppercase', color: 'var(--text-secondary)' }}>
          Score Breakdown
        </h5>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          {Object.entries(breakdown).map(([key, val]) => (
            <div key={key} style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <span style={{ width: '120px', fontSize: '13px', textTransform: 'capitalize', color: 'var(--text-secondary)' }}>
                {key.replace('_', ' ')}
              </span>
              <div style={{ flex: 1, height: '8px', background: 'var(--border-subtle, #f3f4f6)', borderRadius: '4px', overflow: 'hidden', position: 'relative' }}>
                <div
                  style={{
                    height: '100%',
                    width: `${val}%`,
                    background: val >= 90 ? '#10b981' : val >= 75 ? '#3b82f6' : val >= 60 ? '#f59e0b' : '#9ca3af',
                    borderRadius: '4px'
                  }}
                />
              </div>
              <span style={{ width: '36px', fontSize: '13px', fontWeight: 700, textAlign: 'right' }}>
                {val}%
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Strengths & Considerations */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
        <div style={{ background: '#f0fdf4', padding: '16px', borderRadius: '12px', border: '1px solid #bbf7d0' }}>
          <h6 style={{ margin: '0 0 8px 0', fontSize: '13.5px', color: '#166534', fontWeight: 700 }}>Top Matching Factors</h6>
          <ul style={{ margin: 0, paddingLeft: '16px', fontSize: '13px', color: '#1f2937', display: 'flex', flexDirection: 'column', gap: '6px' }}>
            {(recruiterAnalysis.strengths || ['Required experience matched', 'Strong technical portfolio alignment']).map((str, idx) => (
              <li key={idx}>{str}</li>
            ))}
          </ul>
        </div>

        <div style={{ background: '#fffbeb', padding: '16px', borderRadius: '12px', border: '1px solid #fef3c7' }}>
          <h6 style={{ margin: '0 0 8px 0', fontSize: '13.5px', color: '#9a3412', fontWeight: 700 }}>Potential Considerations</h6>
          <ul style={{ margin: 0, paddingLeft: '16px', fontSize: '13px', color: '#1f2937', display: 'flex', flexDirection: 'column', gap: '6px' }}>
            {(recruiterAnalysis.considerations || ['Verify timezone preference', 'Check library versions alignment']).map((con, idx) => (
              <li key={idx}>{con}</li>
            ))}
          </ul>
        </div>
      </div>

      {recruiterAnalysis.placement_advice && (
        <div style={{ background: '#f5f3ff', padding: '16px', borderRadius: '12px', border: '1px solid #ddd6fe' }}>
          <h6 style={{ margin: '0 0 6px 0', fontSize: '13.5px', color: '#5b21b6', fontWeight: 700 }}>AI Hiring Recommendation</h6>
          <p style={{ margin: 0, fontSize: '13px', lineHeight: 1.5, color: '#1f2937' }}>
            {recruiterAnalysis.placement_advice}
          </p>
        </div>
      )}

      {/* Recruiter Feedback Loop */}
      <div
        style={{
          borderTop: '1px solid var(--border-subtle, #f3f4f6)',
          paddingTop: '20px',
          marginTop: '10px'
        }}
      >
        <h6 style={{ margin: '0 0 12px 0', fontSize: '14px', fontWeight: 700 }}>Was this AI Match useful?</h6>
        
        {feedbackSubmitted ? (
          <div style={{ fontSize: '13px', color: '#10b981', fontWeight: 600 }}>
            ✓ Thank you for your feedback! This helps train our match intelligence engine.
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div style={{ display: 'flex', gap: '12px' }}>
              <button
                type="button"
                className={`btn ${rating === 'helpful' ? 'btn--success' : 'btn--outline'}`}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: '8px 16px',
                  borderRadius: '8px',
                  fontWeight: 600,
                  cursor: 'pointer',
                  border: '1px solid ' + (rating === 'helpful' ? '#10b981' : 'var(--border)'),
                  background: rating === 'helpful' ? '#10b981' : 'transparent',
                  color: rating === 'helpful' ? '#ffffff' : 'var(--text)'
                }}
                onClick={() => handleRatingClick('helpful')}
              >
                👍 Helpful
              </button>

              <button
                type="button"
                className={`btn ${rating === 'not_helpful' ? 'btn--danger' : 'btn--outline'}`}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: '8px 16px',
                  borderRadius: '8px',
                  fontWeight: 600,
                  cursor: 'pointer',
                  border: '1px solid ' + (rating === 'not_helpful' ? '#ef4444' : 'var(--border)'),
                  background: rating === 'not_helpful' ? '#ef4444' : 'transparent',
                  color: rating === 'not_helpful' ? '#ffffff' : 'var(--text)'
                }}
                onClick={() => handleRatingClick('not_helpful')}
              >
                👎 Not Helpful
              </button>
            </div>

            {rating && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', animation: 'fadeIn 0.2s' }}>
                <label style={{ fontSize: '13.5px', fontWeight: 600, color: 'var(--text-secondary)' }}>
                  Please select a primary reason:
                </label>
                <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                  {feedbackReasons.map((reason) => (
                    <button
                      key={reason}
                      type="button"
                      style={{
                        padding: '6px 12px',
                        borderRadius: '6px',
                        border: '1px solid ' + (selectedReason === reason ? 'var(--accent)' : 'var(--border)'),
                        background: selectedReason === reason ? 'var(--accent-subtle, #eff6ff)' : 'transparent',
                        color: selectedReason === reason ? 'var(--accent)' : 'var(--text)',
                        fontSize: '12px',
                        cursor: 'pointer'
                      }}
                      onClick={() => setSelectedReason(reason)}
                    >
                      {reason}
                    </button>
                  ))}
                </div>

                <button
                  type="button"
                  className="btn btn--primary"
                  style={{
                    alignSelf: 'flex-start',
                    padding: '8px 20px',
                    borderRadius: '8px',
                    fontWeight: 700,
                    cursor: 'pointer',
                    background: 'var(--accent)',
                    color: '#ffffff',
                    border: 'none',
                    marginTop: '8px'
                  }}
                  disabled={loading}
                  onClick={submitFeedback}
                >
                  {loading ? 'Submitting...' : 'Submit Feedback'}
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
