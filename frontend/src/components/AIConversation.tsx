import { useState } from 'react'
import ToolExecutionCard from './ToolExecutionCard'

interface Message {
  id: string
  role: 'user' | 'assistant'
  message: string
  execution_graph?: any
  plan_confidence?: number
  plan_confidence_reason?: string
  plan_approved: boolean
  tool_calls: any[]
}

interface AIConversationProps {
  messages: Message[]
  streaming: boolean
  activeStatuses: any[]
  onExecutePlan: (messageId: string) => void
  onCancelPlan: () => void
  onFeedbackSubmit: (messageId: string, feedback: string) => Promise<void>
}

export default function AIConversation({
  messages = [],
  streaming,
  activeStatuses = [],
  onExecutePlan,
  onCancelPlan,
  onFeedbackSubmit
}: AIConversationProps) {
  const [feedbackState, setFeedbackState] = useState<Record<string, string>>({})
  const [feedbackSubmitted, setFeedbackSubmitted] = useState<Record<string, boolean>>({})

  const handleFeedback = async (msgId: string, type: string) => {
    setFeedbackState((prev) => ({ ...prev, [msgId]: type }))
    try {
      await onFeedbackSubmit(msgId, type)
      setFeedbackSubmitted((prev) => ({ ...prev, [msgId]: true }))
    } catch (err) {
      console.error(err)
    }
  }

  const feedbackOptions = [
    { label: '👍 Helpful', val: 'helpful' },
    { label: '❌ Incorrect', val: 'incorrect' },
    { label: '⚠️ Incomplete', val: 'incomplete' },
    { label: '🔮 Hallucinated', val: 'hallucinated' },
    { label: '🐢 Too Slow', val: 'too_slow' },
    { label: '🔒 Permission Error', val: 'permission_error' }
  ]

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '24px',
        fontFamily: 'var(--font-sans, sans-serif)',
        paddingBottom: '24px'
      }}
    >
      {messages.map((msg) => {
        const isUser = msg.role === 'user'
        const hasGraph = msg.execution_graph && !msg.plan_approved

        return (
          <div
            key={msg.id}
            style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: isUser ? 'flex-end' : 'flex-start',
              gap: '6px',
              maxWidth: '85%',
              alignSelf: isUser ? 'flex-end' : 'flex-start'
            }}
          >
            {/* Sender Label */}
            <span style={{ fontSize: '11px', color: 'var(--text-tertiary)', fontWeight: 700 }}>
              {isUser ? 'Recruiter' : 'AI Recruiting Agent'}
            </span>

            {/* Bubble */}
            <div
              style={{
                background: isUser ? 'var(--accent, #3b82f6)' : 'var(--bg-card, #ffffff)',
                color: isUser ? '#ffffff' : 'var(--text)',
                border: isUser ? 'none' : '1px solid var(--border, #e5e7eb)',
                borderRadius: '16px',
                padding: '16px 20px',
                fontSize: '14.5px',
                lineHeight: 1.6,
                boxShadow: isUser ? 'none' : 'var(--shadow-premium, 0 4px 20px -6px rgba(0,0,0,0.02))'
              }}
            >
              <div style={{ whiteSpace: 'pre-wrap' }}>{msg.message}</div>

              {/* Pre-execution Planning Checkpoint */}
              {hasGraph && (
                <div
                  style={{
                    marginTop: '16px',
                    paddingTop: '16px',
                    borderTop: '1px solid var(--border-subtle, #f3f4f6)',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '12px'
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: '12px', fontWeight: 700, color: 'var(--text-secondary)' }}>
                      Proposed Plan (Confidence: {msg.plan_confidence}%)
                    </span>
                    <span style={{ fontSize: '11px', color: 'var(--text-tertiary)' }}>
                      {msg.plan_confidence_reason}
                    </span>
                  </div>

                  {/* Plan cost estimates */}
                  <div
                    style={{
                      display: 'grid',
                      gridTemplateColumns: 'repeat(4, 1fr)',
                      gap: '8px',
                      background: 'var(--bg-subtle, #f9fafb)',
                      padding: '10px',
                      borderRadius: '8px',
                      fontSize: '11.5px',
                      border: '1px solid var(--border-subtle)'
                    }}
                  >
                    <div>
                      <strong style={{ display: 'block' }}>Tools</strong>
                      {msg.execution_graph.estimated_tools}
                    </div>
                    <div>
                      <strong style={{ display: 'block' }}>Est. Time</strong>
                      {msg.execution_graph.estimated_time_seconds}s
                    </div>
                    <div>
                      <strong style={{ display: 'block' }}>Est. Tokens</strong>
                      {msg.execution_graph.estimated_tokens}
                    </div>
                    <div>
                      <strong style={{ display: 'block' }}>Cache Prob.</strong>
                      {msg.execution_graph.cache_hit_probability}%
                    </div>
                  </div>

                  {/* Graph Steps list */}
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', fontSize: '12.5px', color: 'var(--text-secondary)' }}>
                    {msg.execution_graph.nodes.map((node: any, idx: number) => (
                      <div key={node.id} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span style={{ color: 'var(--accent)', fontWeight: 700 }}>{idx + 1}.</span>
                        <span style={{ textTransform: 'capitalize' }}>
                          {node.tool ? node.tool.replace('_', ' ') : 'Evaluate branch conditions'}
                        </span>
                        <span style={{ fontSize: '10px', color: 'var(--text-tertiary)', background: 'rgba(0,0,0,0.03)', padding: '1px 4px', borderRadius: '4px' }}>
                          {node.approval_level}
                        </span>
                      </div>
                    ))}
                  </div>

                  {/* Approval execute button */}
                  <button
                    type="button"
                    className="btn btn--primary"
                    style={{
                      marginTop: '8px',
                      padding: '8px 16px',
                      background: 'var(--accent)',
                      color: '#ffffff',
                      border: 'none',
                      borderRadius: '8px',
                      fontWeight: 700,
                      cursor: 'pointer',
                      alignSelf: 'flex-start'
                    }}
                    onClick={() => onExecutePlan(msg.id)}
                  >
                    Confirm & Execute Plan
                  </button>
                </div>
              )}

              {/* Tool Execution logs */}
              {msg.tool_calls.length > 0 && (
                <ToolExecutionCard statuses={msg.tool_calls} />
              )}
            </div>

            {/* Granular Feedback Rating */}
            {!isUser && !hasGraph && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '4px' }}>
                {feedbackSubmitted[msg.id] ? (
                  <span style={{ fontSize: '11px', color: '#10b981', fontWeight: 650 }}>
                    ✓ Feedback submitted.
                  </span>
                ) : (
                  <>
                    <span style={{ fontSize: '11px', color: 'var(--text-tertiary)' }}>Rate Answer:</span>
                    <div style={{ display: 'flex', gap: '4px' }}>
                      {feedbackOptions.map((opt) => (
                        <button
                          key={opt.val}
                          type="button"
                          style={{
                            padding: '2px 8px',
                            borderRadius: '4px',
                            border: '1px solid ' + (feedbackState[msg.id] === opt.val ? 'var(--accent)' : 'var(--border)'),
                            background: feedbackState[msg.id] === opt.val ? 'var(--accent-subtle)' : 'transparent',
                            color: 'var(--text-secondary)',
                            fontSize: '11px',
                            cursor: 'pointer'
                          }}
                          onClick={() => handleFeedback(msg.id, opt.val)}
                        >
                          {opt.label}
                        </button>
                      ))}
                    </div>
                  </>
                )}
              </div>
            )}
          </div>
        )
      })}

      {/* Streaming Active execution timeline progress and cancel controls */}
      {streaming && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', alignSelf: 'flex-start', maxWidth: '85%' }}>
          <span style={{ fontSize: '11px', color: 'var(--text-tertiary)', fontWeight: 700 }}>AI Agent Engine</span>
          <div
            style={{
              background: 'var(--bg-card)',
              border: '1px solid var(--border)',
              borderRadius: '16px',
              padding: '16px 20px',
              boxShadow: 'var(--shadow-premium)'
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
              <span className="spinner" style={{ animation: 'spin 1s linear infinite', display: 'inline-block', width: '12px', height: '12px', border: '2px solid var(--accent)', borderTopColor: 'transparent', borderRadius: '50%' }} />
              <span style={{ fontSize: '13.5px', fontWeight: 600 }}>Executing Plan Graph...</span>
            </div>
            <ToolExecutionCard statuses={activeStatuses} />

            <button
              type="button"
              className="btn btn--outline"
              style={{
                marginTop: '12px',
                fontSize: '12px',
                padding: '6px 12px',
                borderRadius: '6px',
                border: '1px solid #ef4444',
                color: '#ef4444',
                background: 'transparent',
                cursor: 'pointer'
              }}
              onClick={onCancelPlan}
            >
              Cancel Execution
            </button>
          </div>
        </div>
      )}

      <style dangerouslySetInnerHTML={{ __html: `
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}} />
    </div>
  )
}
