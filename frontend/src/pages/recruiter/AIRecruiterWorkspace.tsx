import { useState } from 'react'
import AppLayout from '../../components/AppLayout'
import AIConversation from '../../components/AIConversation'
import AIActionCard from '../../components/AIActionCard'
import AIRecommendationPanel from '../../components/AIRecommendationPanel'
import CandidateComparison from '../../components/CandidateComparison'

interface Session {
  id: string
  session_name: string
  current_job_id?: string
  current_pool_id?: string
  current_filters: any
  selected_candidate_ids: string[]
  context_version: number
}

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

export default function AIRecruiterWorkspace() {
  const [sessions, setSessions] = useState<Session[]>([
    { id: 'sess-1', session_name: 'Engineering Hiring', current_filters: { location: 'Bangalore' }, selected_candidate_ids: [], context_version: 1 },
    { id: 'sess-2', session_name: 'Campus Sourcing 2026', current_filters: {}, selected_candidate_ids: [], context_version: 3 }
  ])

  const [activeSession, setActiveSession] = useState<Session>(sessions[0])
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'msg-1',
      role: 'assistant',
      message: 'Hello! I am your AI Sourcing Agent. Ask me to find candidates, compare active profiles, or view analytics reports.',
      plan_approved: true,
      tool_calls: []
    }
  ])

  const [prompt, setPrompt] = useState('')
  const [streaming, setStreaming] = useState(false)
  const [activeStatuses, setActiveStatuses] = useState<any[]>([])
  
  // Pending actions queue
  const [pendingActions, setPendingActions] = useState([
    { id: 'action-1', type: 'draft_email', details: 'Draft rejection email for John Doe' },
    { id: 'action-2', type: 'add_to_pool', details: 'Add Marcus Wright to React Developers static pool' }
  ])

  // Candidates comparison data
  const [comparedCandidates, setComparedCandidates] = useState<any[]>([])

  // Right sidebar pinned candidates list
  const pinnedCandidates = [
    { id: 'ff8ad11b-f3c2-414c-bf3c-51fb5743d0a3', name: 'John Doe', score: 92 },
    { id: 'cand-2', name: 'Marcus Wright', score: 86 }
  ]

  // Suggested next steps
  const suggestions = ['Compare candidates', 'Generate interview guide']

  const handleCreateSession = () => {
    const name = window.prompt('Enter workspace session name:')
    if (!name) return
    const newSess: Session = {
      id: `sess-${Date.now()}`,
      session_name: name,
      current_filters: {},
      selected_candidate_ids: [],
      context_version: 1
    }
    setSessions([...sessions, newSess])
    setActiveSession(newSess)
    setMessages([
      {
        id: `msg-${Date.now()}`,
        role: 'assistant',
        message: `Hello! Switched to workspace session: ${name}. How can I assist you?`,
        plan_approved: true,
        tool_calls: []
      }
    ])
  }

  const handleSendMessage = (e: React.FormEvent) => {
    e.preventDefault()
    if (!prompt) return

    const userMsg: Message = {
      id: `msg-user-${Date.now()}`,
      role: 'user',
      message: prompt,
      plan_approved: true,
      tool_calls: []
    }

    setMessages((prev) => [...prev, userMsg])
    setPrompt('')

    // Generate proposed plan after 600ms
    setTimeout(() => {
      const planMsg: Message = {
        id: `msg-plan-${Date.now()}`,
        role: 'assistant',
        message: 'Plan generated successfully. Confirm to execute.',
        plan_confidence: 96,
        plan_confidence_reason: 'Clear recruiter search criteria detected.',
        plan_approved: false,
        execution_graph: {
          estimated_tools: 2,
          estimated_time_seconds: 2.4,
          estimated_tokens: 3000,
          cache_hit_probability: 85,
          nodes: [
            { id: 'node_search', tool: 'search_candidates', approval_level: 'read_only' },
            { id: 'node_compare', tool: 'compare_candidates', approval_level: 'read_only' }
          ]
        },
        tool_calls: []
      }
      setMessages((prev) => [...prev, planMsg])
    }, 600)
  }

  const handleExecutePlan = (msgId: string) => {
    // Transition to streaming execution timeline
    setMessages((prev) =>
      prev.map((m) => (m.id === msgId ? { ...m, plan_approved: true } : m))
    )
    setStreaming(true)
    setActiveStatuses([
      { node_id: 'node_search', tool: 'search_candidates', status: 'running' },
      { node_id: 'node_compare', tool: 'compare_candidates', status: 'pending' }
    ])

    // Update steps
    setTimeout(() => {
      setActiveStatuses([
        { node_id: 'node_search', tool: 'search_candidates', status: 'success' },
        { node_id: 'node_compare', tool: 'compare_candidates', status: 'running' }
      ])
    }, 1000)

    setTimeout(() => {
      setActiveStatuses([
        { node_id: 'node_search', tool: 'search_candidates', status: 'success' },
        { node_id: 'node_compare', tool: 'compare_candidates', status: 'success' }
      ])
    }, 2000)

    // Complete execution and append summary
    setTimeout(() => {
      setStreaming(false)
      const finalMsg: Message = {
        id: `msg-done-${Date.now()}`,
        role: 'assistant',
        message: 'Here is the agent summary:\n- Search candidates found: 3 profiles.\n- Successfully completed side-by-side candidate comparison.',
        plan_approved: true,
        tool_calls: [
          { node_id: 'node_search', tool: 'search_candidates', status: 'success' },
          { node_id: 'node_compare', tool: 'compare_candidates', status: 'success' }
        ]
      }
      setMessages((prev) => [...prev, finalMsg])
      
      // Load candidate comparison table data
      setComparedCandidates([
        {
          id: 'cand-1',
          name: 'John Doe',
          email: 'john.doe@example.com',
          experience_years: '6 years',
          skills: 'React, Python, Go',
          match_score: 92,
          score_bar: '',
          strengths: ['Expert in system concurrency', 'Strong portfolio alignment'],
          concerns: []
        },
        {
          id: 'cand-2',
          name: 'Marcus Wright',
          email: 'marcus.wright@cyberdyne.com',
          experience_years: '5 years',
          skills: 'React, NodeJS, Python',
          match_score: 86,
          score_bar: '',
          strengths: ['Fullstack React developer', 'Strong backend familiarity'],
          concerns: ['Timezone offset review required']
        }
      ])
    }, 2500)
  }

  const handleCancelExecution = () => {
    setStreaming(false)
  }

  const handleActionQueue = (actionId: string, approved: boolean) => {
    setPendingActions((prev) => prev.filter((a) => a.id !== actionId))
    if (approved) {
      alert('Recruiter approved action successfully.')
    } else {
      alert('Recruiter rejected action.')
    }
  }

  const handleFeedbackSubmit = async (msgId: string, feedback: string) => {
    console.log(`Feedback submitted for message ${msgId}: ${feedback}`)
  }

  return (
    <AppLayout>
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '200px 1fr 240px',
          height: 'calc(100vh - var(--header-h) - 40px)',
          background: 'var(--bg)',
          fontFamily: 'var(--font-sans, sans-serif)',
          color: 'var(--text)',
          borderRadius: '16px',
          border: '1px solid var(--border)',
          overflow: 'hidden'
        }}
      >
        {/* Left Panel: Session Sidebar */}
        <div style={{ background: 'var(--bg-card)', borderRight: '1px solid var(--border)', padding: '20px 12px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h3 style={{ margin: 0, fontSize: '14.5px', fontWeight: 700 }}>AI Workspaces</h3>
            <button
              type="button"
              style={{ fontSize: '11px', padding: '3px 8px', background: 'var(--accent)', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
              onClick={handleCreateSession}
            >
              + New
            </button>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            {sessions.map((sess) => (
              <button
                key={sess.id}
                type="button"
                style={{
                  textAlign: 'left',
                  padding: '10px 12px',
                  borderRadius: '6px',
                  fontSize: '12.5px',
                  fontWeight: activeSession.id === sess.id ? 700 : 550,
                  color: activeSession.id === sess.id ? 'var(--accent)' : 'var(--text-secondary)',
                  background: activeSession.id === sess.id ? 'var(--accent-subtle)' : 'transparent',
                  border: 'none',
                  cursor: 'pointer'
                }}
                onClick={() => {
                  setActiveSession(sess)
                  setMessages([
                    {
                      id: `msg-${Date.now()}`,
                      role: 'assistant',
                      message: `Restored workspace thread: ${sess.session_name}.`,
                      plan_approved: true,
                      tool_calls: []
                    }
                  ])
                  setComparedCandidates([])
                }}
              >
                💬 {sess.session_name}
              </button>
            ))}
          </div>
        </div>

        {/* Center Panel: Conversations Feed */}
        <div style={{ display: 'flex', flexDirection: 'column', height: '100%', background: 'var(--bg)' }}>
          <div style={{ flex: 1, padding: '24px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {/* Conversations List */}
            <AIConversation
              messages={messages}
              streaming={streaming}
              activeStatuses={activeStatuses}
              onExecutePlan={handleExecutePlan}
              onCancelPlan={handleCancelExecution}
              onFeedbackSubmit={handleFeedbackSubmit}
            />

            {/* Candidate comparisons rendering inside flow */}
            <CandidateComparison candidates={comparedCandidates} />

            {/* AI queue action triggers */}
            <AIActionCard actions={pendingActions} onAction={handleActionQueue} />

            {/* Recommended next steps */}
            <AIRecommendationPanel suggestions={suggestions} onSelectSuggestion={(s) => alert(`Executing suggestion: ${s}`)} />
          </div>

          {/* Prompt Entry Form */}
          <form
            onSubmit={handleSendMessage}
            style={{
              padding: '16px 24px',
              borderTop: '1px solid var(--border)',
              background: 'var(--bg-card)',
              display: 'flex',
              gap: '12px'
            }}
          >
            <input
              type="text"
              placeholder="Ask the AI Recruiting Agent (e.g. Compare candidates, search backend devs)"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              style={{
                flex: 1,
                padding: '12px 16px',
                borderRadius: '8px',
                border: '1px solid var(--border)',
                outline: 'none',
                background: 'var(--bg)'
              }}
            />
            <button
              type="submit"
              style={{
                padding: '0 20px',
                borderRadius: '8px',
                background: 'var(--accent)',
                color: '#ffffff',
                border: 'none',
                fontWeight: 700,
                cursor: 'pointer'
              }}
            >
              Ask Agent
            </button>
          </form>
        </div>

        {/* Right Sidebar: Context Snapshot Panel */}
        <div style={{ background: 'var(--bg-card)', borderLeft: '1px solid var(--border)', padding: '24px 16px', display: 'flex', flexDirection: 'column', gap: '24px' }}>
          <div>
            <h4 style={{ margin: 0, fontSize: '13px', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-secondary)' }}>
              Current Context
            </h4>
            <span style={{ fontSize: '11px', color: 'var(--text-tertiary)' }}>
              Version {activeSession.context_version} • Snapshotted
            </span>
          </div>

          <div>
            <span style={{ fontSize: '12px', fontWeight: 650, display: 'block', color: 'var(--text-secondary)' }}>Active Job:</span>
            <span style={{ fontSize: '13px', color: 'var(--text)' }}>
              {activeSession.current_job_id || 'Senior React Engineer'}
            </span>
          </div>

          <div>
            <span style={{ fontSize: '12px', fontWeight: 650, display: 'block', color: 'var(--text-secondary)' }}>Active Filters:</span>
            <pre style={{ margin: '4px 0 0 0', fontSize: '11px', background: '#f3f4f6', padding: '6px', borderRadius: '4px' }}>
              {JSON.stringify(activeSession.current_filters, null, 2)}
            </pre>
          </div>

          {/* Pinned Candidates */}
          <div>
            <span style={{ fontSize: '12px', fontWeight: 650, display: 'block', color: 'var(--text-secondary)', marginBottom: '8px' }}>
              📌 Pinned Candidates
            </span>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              {pinnedCandidates.map((c) => (
                <div key={c.id} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12.5px', background: 'var(--bg)', padding: '6px 8px', borderRadius: '4px' }}>
                  <span>{c.name}</span>
                  <span style={{ fontWeight: 700, color: '#10b981' }}>{c.score}%</span>
                </div>
              ))}
            </div>
          </div>

          <div style={{ borderTop: '1px solid var(--border)', paddingTop: '20px', marginTop: 'auto' }}>
            <span style={{ fontSize: '11px', color: 'var(--text-tertiary)', fontStyle: 'italic', display: 'block', lineHeight: 1.4 }}>
              The Agent planner is provider-agnostic. Orchestration, validation, and memory execution remain independent of LLM models.
            </span>
          </div>
        </div>
      </div>
    </AppLayout>
  )
}
