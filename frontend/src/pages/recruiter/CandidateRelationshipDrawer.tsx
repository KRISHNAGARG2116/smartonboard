import { useState } from 'react'
import MatchAnalysisDrawer from '../../components/MatchAnalysisDrawer'

interface CandidateRelationshipDrawerProps {
  candidateId: string
  jobId: string
  onClose: () => void
}

type TabType = 'timeline' | 'match' | 'similar' | 'merge'

export default function CandidateRelationshipDrawer({
  candidateId,
  jobId,
  onClose
}: CandidateRelationshipDrawerProps) {
  const [activeTab, setActiveTab] = useState<TabType>('timeline')
  
  // Relationship states
  const [crmStage, setCrmStage] = useState('new_lead')
  const [owner, setOwner] = useState('Sarah Connor')
  const [secondaryOwner, setSecondaryOwner] = useState('John Connor')
  const [watchers, setWatchers] = useState<string[]>(['T-800'])
  
  // Overrides
  const [isPinned, setIsPinned] = useState(false)
  const [isFavorite, setIsFavorite] = useState(false)
  const [ignoreAiMatch, setIgnoreAiMatch] = useState(false)

  // Timeline state & filters
  const [timelineFilter, setTimelineFilter] = useState('all')
  const timelineEvents = [
    { type: 'applications', title: 'Applied for Senior Backend Engineer', time: '2 hours ago', desc: 'Applied directly via Candidate Portal.' },
    { type: 'emails', title: 'Outreach Sequence Enrolled', time: '1 day ago', desc: 'Enrolled in React Sourcing Campaign by Sarah Connor.' },
    { type: 'pools', title: 'Added to Talent Pool', time: '2 days ago', desc: 'Added to static pool: SF React Leads by Sarah Connor.' },
    { type: 'notes', title: 'Recruiter Note Added', time: '3 days ago', desc: "Sarah Connor: 'Spoke briefly at the SF tech meetup. Strong React background.'" }
  ]

  // Similar Candidate comparison table states
  const comparedCandidates = [
    { name: 'John Doe (Current)', skills: 'React, Python, Go', exp: '6 years', match: 92, notes: 'Target candidate' },
    { name: 'Marcus Wright', skills: 'React, NodeJS, Python', exp: '5 years', match: 86, notes: 'Lookalike candidate' },
    { name: 'Kyle Reese', skills: 'React, TypeScript, CSS', exp: '4 years', match: 74, notes: 'Lookalike candidate' }
  ]

  // Merge states
  const [mergeTarget, setMergeTarget] = useState('')
  const [mergePreview, setMergePreview] = useState<any | null>(null)
  const [mergeHistory, setMergeHistory] = useState<any[]>([])

  const handlePreviewMerge = () => {
    setMergePreview({
      surviving: { name: 'John Doe', email: 'john.doe@example.com', phone: '+15105550192', location: 'San Francisco, CA' },
      merged: { name: 'J. Doe', email: 'j.doe@example.com', phone: '+15105550192', location: 'SF, California' }
    })
  }

  const handleExecuteMerge = () => {
    setMergeHistory([...mergeHistory, { id: 'merge-1', date: 'Just now', surviving: 'John Doe', merged: 'J. Doe' }])
    setMergePreview(null)
    setMergeTarget('')
  }

  const handleUndoMerge = (id: string) => {
    setMergeHistory(mergeHistory.filter(h => h.id !== id))
  }

  const handleFeedbackSubmit = async (rating: 'helpful' | 'not_helpful', reason?: string) => {
    // API request stub to POST /api/v1/match/feedback
    console.log('Match feedback submitted:', { candidateId, jobId, rating, reason })
  }

  const filteredTimeline = timelineFilter === 'all'
    ? timelineEvents
    : timelineEvents.filter(e => e.type === timelineFilter)

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        right: 0,
        bottom: 0,
        width: '840px',
        background: 'var(--bg-card)',
        borderLeft: '1px solid var(--border)',
        boxShadow: '0 0 40px rgba(0,0,0,0.15)',
        zIndex: 500,
        display: 'grid',
        gridTemplateColumns: '2.5fr 1fr',
        fontFamily: 'var(--font-sans, sans-serif)',
        animation: 'slideIn 0.3s cubic-bezier(0.16, 1, 0.3, 1)'
      }}
    >
      {/* Main Panel */}
      <div style={{ padding: '32px', display: 'flex', flexDirection: 'column', gap: '24px', overflowY: 'auto', borderRight: '1px solid var(--border)' }}>
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <h2 style={{ margin: 0, fontSize: '22px', fontWeight: 800 }}>John Doe</h2>
            <span style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
              john.doe@example.com • +1 510 555 0192
            </span>
          </div>
          <button
            type="button"
            className="btn btn--outline"
            style={{ fontSize: '12px', padding: '6px 12px', borderRadius: '6px', cursor: 'pointer' }}
            onClick={onClose}
          >
            Close Card
          </button>
        </div>

        {/* Tab Controls */}
        <div style={{ display: 'flex', gap: '16px', borderBottom: '1px solid var(--border)' }}>
          {(['timeline', 'match', 'similar', 'merge'] as const).map(tab => (
            <button
              key={tab}
              type="button"
              style={{
                padding: '12px 8px',
                fontSize: '13.5px',
                fontWeight: activeTab === tab ? 700 : 500,
                color: activeTab === tab ? 'var(--accent)' : 'var(--text-secondary)',
                borderBottom: '2px solid ' + (activeTab === tab ? 'var(--accent)' : 'transparent'),
                background: 'transparent',
                border: 'none',
                cursor: 'pointer',
                textTransform: 'capitalize'
              }}
              onClick={() => setActiveTab(tab)}
            >
              {tab === 'match' ? 'AI Match Analysis' : tab === 'similar' ? 'Lookalikes' : tab}
            </button>
          ))}
        </div>

        {/* Tab Contents */}
        <div style={{ flex: 1 }}>
          {activeTab === 'timeline' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
              <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                {['all', 'emails', 'interviews', 'notes', 'applications', 'pools', 'system_events'].map(filter => (
                  <button
                    key={filter}
                    type="button"
                    style={{
                      padding: '4px 10px',
                      borderRadius: '4px',
                      border: '1px solid ' + (timelineFilter === filter ? 'var(--accent)' : 'var(--border)'),
                      background: timelineFilter === filter ? 'var(--accent-subtle)' : 'transparent',
                      color: timelineFilter === filter ? 'var(--accent)' : 'var(--text-secondary)',
                      fontSize: '11.5px',
                      cursor: 'pointer',
                      textTransform: 'capitalize'
                    }}
                    onClick={() => setTimelineFilter(filter)}
                  >
                    {filter.replace('_', ' ')}
                  </button>
                ))}
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', borderLeft: '2px solid var(--border)', paddingLeft: '20px', marginLeft: '8px' }}>
                {filteredTimeline.map((evt, idx) => (
                  <div key={idx} style={{ position: 'relative' }}>
                    <div style={{ position: 'absolute', left: '-27px', top: '4px', width: '12px', height: '12px', borderRadius: '50%', background: 'var(--accent)', border: '2px solid var(--bg)' }} />
                    <h5 style={{ margin: 0, fontSize: '13.5px', fontWeight: 650 }}>{evt.title}</h5>
                    <span style={{ fontSize: '11px', color: 'var(--text-tertiary)' }}>{evt.time}</span>
                    <p style={{ margin: '6px 0 0 0', fontSize: '13px', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                      {evt.desc}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {activeTab === 'match' && (
            <MatchAnalysisDrawer
              candidateId={candidateId}
              jobId={jobId}
              score={92}
              confidence="high"
              confidenceExplanation={['Required skills verified', 'Resume complete', 'Structured experience detected']}
              breakdown={{
                skills: 95,
                experience: 90,
                industry: 85,
                location: 100,
                education: 75,
                role_alignment: 80
              }}
              recruiterAnalysis={{
                strengths: ['Expert in React and TypeScript ecosystems', 'Over 6 years of backend engineering depth'],
                considerations: ['Relocation confirmation required', 'Review salary expectations match'],
                placement_advice: 'Candidate displays outstanding technical parameters. Recommend fast-tracking to final panel.'
              }}
              onSubmitFeedback={handleFeedbackSubmit}
            />
          )}

          {activeTab === 'similar' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
              <h4 style={{ margin: 0, fontSize: '15px', fontWeight: 700 }}>Side-by-Side Comparison</h4>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--border)', textAlign: 'left', color: 'var(--text-secondary)' }}>
                    <th style={{ padding: '8px' }}>Candidate</th>
                    <th style={{ padding: '8px' }}>Skills</th>
                    <th style={{ padding: '8px' }}>Experience</th>
                    <th style={{ padding: '8px' }}>Match Score</th>
                    <th style={{ padding: '8px' }}>Notes</th>
                  </tr>
                </thead>
                <tbody>
                  {comparedCandidates.map((cand, idx) => (
                    <tr key={idx} style={{ borderBottom: '1px solid var(--border-subtle, #f3f4f6)' }}>
                      <td style={{ padding: '12px 8px', fontWeight: 650 }}>{cand.name}</td>
                      <td style={{ padding: '12px 8px' }}>{cand.skills}</td>
                      <td style={{ padding: '12px 8px' }}>{cand.exp}</td>
                      <td style={{ padding: '12px 8px', fontWeight: 700, color: '#10b981' }}>{cand.match}%</td>
                      <td style={{ padding: '12px 8px', color: 'var(--text-secondary)' }}>{cand.notes}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {activeTab === 'merge' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
              <h4 style={{ margin: 0, fontSize: '15px', fontWeight: 700 }}>Merge Duplicate Candidates</h4>
              <div style={{ display: 'flex', gap: '8px' }}>
                <input
                  type="text"
                  placeholder="Enter duplicate candidate email or name"
                  value={mergeTarget}
                  onChange={e => setMergeTarget(e.target.value)}
                  style={{ flex: 1, padding: '8px', borderRadius: '6px', border: '1px solid var(--border)' }}
                />
                <button
                  type="button"
                  className="btn btn--primary"
                  style={{ background: 'var(--accent)', color: '#fff', border: 'none', padding: '8px 16px', borderRadius: '6px', cursor: 'pointer' }}
                  onClick={handlePreviewMerge}
                >
                  Preview Merge
                </button>
              </div>

              {mergePreview && (
                <div style={{ border: '1px solid #bfdbfe', background: '#eff6ff', borderRadius: '12px', padding: '16px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
                  <h5 style={{ margin: 0, fontSize: '14px', fontWeight: 700, color: 'var(--accent)' }}>Merge Preview</h5>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', fontSize: '13px' }}>
                    <div>
                      <strong>Surviving Record:</strong>
                      <p style={{ margin: '4px 0 0 0' }}>{mergePreview.surviving.name} ({mergePreview.surviving.email})</p>
                    </div>
                    <div>
                      <strong>Merged (Duplicate):</strong>
                      <p style={{ margin: '4px 0 0 0' }}>{mergePreview.merged.name} ({mergePreview.merged.email})</p>
                    </div>
                  </div>
                  <button
                    type="button"
                    className="btn btn--primary"
                    style={{ background: 'var(--accent)', color: '#fff', border: 'none', padding: '8px 16px', borderRadius: '8px', cursor: 'pointer', alignSelf: 'flex-start' }}
                    onClick={handleExecuteMerge}
                  >
                    Confirm & Execute Merge
                  </button>
                </div>
              )}

              {mergeHistory.length > 0 && (
                <div>
                  <h5 style={{ margin: '16px 0 8px 0', fontSize: '14px', fontWeight: 700 }}>Merge History Logs</h5>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    {mergeHistory.map(h => (
                      <div key={h.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', border: '1px solid var(--border)', padding: '12px', borderRadius: '6px' }}>
                        <span style={{ fontSize: '13px' }}>
                          Merged {h.merged} into {h.surviving} ({h.date})
                        </span>
                        <button
                          type="button"
                          className="btn btn--outline"
                          style={{ fontSize: '11px', padding: '4px 8px', borderRadius: '4px', cursor: 'pointer' }}
                          onClick={() => handleUndoMerge(h.id)}
                        >
                          Undo Merge
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Sidebar Controls Panel */}
      <div style={{ padding: '32px 20px', background: 'var(--color-fog, #f9fafb)', display: 'flex', flexDirection: 'column', gap: '24px' }}>
        {/* Stage Tracking */}
        <div>
          <label style={{ fontSize: '12px', textTransform: 'uppercase', fontWeight: 700, color: 'var(--text-secondary)', display: 'block', marginBottom: '8px' }}>
            CRM Pipeline Stage
          </label>
          <select
            value={crmStage}
            onChange={e => setCrmStage(e.target.value)}
            style={{ width: '100%', padding: '8px', borderRadius: '6px', border: '1px solid var(--border)' }}
          >
            <option value="new_lead">New Lead</option>
            <option value="attempting_contact">Attempting Contact</option>
            <option value="contacted">Contacted</option>
            <option value="conversation_started">Conversation Started</option>
            <option value="interested">Interested</option>
            <option value="talent_pool">Talent Pool</option>
            <option value="ready_for_opening">Ready for Opening</option>
            <option value="submitted">Submitted</option>
            <option value="archived">Archived</option>
            <option value="do_not_contact">Do Not Contact</option>
          </select>
        </div>

        {/* Ownership */}
        <div>
          <label style={{ fontSize: '12px', textTransform: 'uppercase', fontWeight: 700, color: 'var(--text-secondary)', display: 'block', marginBottom: '8px' }}>
            Relationship Owner
          </label>
          <input
            type="text"
            value={owner}
            onChange={e => setOwner(e.target.value)}
            style={{ width: '100%', padding: '8px', borderRadius: '6px', border: '1px solid var(--border)', fontSize: '13px' }}
          />
        </div>

        <div>
          <label style={{ fontSize: '12px', textTransform: 'uppercase', fontWeight: 700, color: 'var(--text-secondary)', display: 'block', marginBottom: '8px' }}>
            Secondary Owner
          </label>
          <input
            type="text"
            value={secondaryOwner}
            onChange={e => setSecondaryOwner(e.target.value)}
            style={{ width: '100%', padding: '8px', borderRadius: '6px', border: '1px solid var(--border)', fontSize: '13px' }}
          />
        </div>

        {/* Watchers */}
        <div>
          <label style={{ fontSize: '12px', textTransform: 'uppercase', fontWeight: 700, color: 'var(--text-secondary)', display: 'block', marginBottom: '8px' }}>
            Watchers (Collaborators)
          </label>
          <input
            type="text"
            value={watchers.join(', ')}
            onChange={e => setWatchers(e.target.value.split(',').map(s => s.trim()))}
            style={{ width: '100%', padding: '8px', borderRadius: '6px', border: '1px solid var(--border)', fontSize: '13px' }}
          />
        </div>

        {/* Overrides */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', borderTop: '1px solid var(--border)', paddingTop: '20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <input type="checkbox" id="pinned" checked={isPinned} onChange={e => setIsPinned(e.target.checked)} />
            <label htmlFor="pinned" style={{ fontSize: '13px', fontWeight: 600 }}>Pin Candidate</label>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <input type="checkbox" id="favorite" checked={isFavorite} onChange={e => setIsFavorite(e.target.checked)} />
            <label htmlFor="favorite" style={{ fontSize: '13px', fontWeight: 600 }}>Favorite Candidate</label>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <input type="checkbox" id="ignore" checked={ignoreAiMatch} onChange={e => setIgnoreAiMatch(e.target.checked)} />
            <label htmlFor="ignore" style={{ fontSize: '13px', fontWeight: 600 }}>Ignore AI Match</label>
          </div>
        </div>

        {/* Sourcing Campaign */}
        <div style={{ borderTop: '1px solid var(--border)', paddingTop: '20px' }}>
          <label style={{ fontSize: '12px', textTransform: 'uppercase', fontWeight: 700, color: 'var(--text-secondary)', display: 'block', marginBottom: '8px' }}>
            Outreach Sequence
          </label>
          <button
            type="button"
            className="btn btn--outline btn--block"
            style={{ width: '100%', padding: '8px 12px', borderRadius: '6px', cursor: 'pointer', fontSize: '13px' }}
            onClick={() => alert('Candidate enrolled in outreach sequence.')}
          >
            🚀 Enroll in Sequence
          </button>
        </div>
      </div>

      <style dangerouslySetInnerHTML={{ __html: `
        @keyframes slideIn {
          from { transform: translateX(100%); }
          to { transform: translateX(0); }
        }
      `}} />
    </div>
  )
}
