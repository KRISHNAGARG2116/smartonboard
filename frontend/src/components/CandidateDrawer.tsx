import { useEffect, useCallback } from 'react'
import ReactMarkdown from 'react-markdown'
import type { RecruitResult } from '../api'
import { scoreClass, decisionBadge } from '../utils/score'

type DrawerTab = 'overview' | 'screening' | 'communication' | 'onboarding'

interface CandidateDrawerProps {
  candidate: RecruitResult
  tab: DrawerTab
  onTabChange: (tab: DrawerTab) => void
  onClose: () => void
}

export default function CandidateDrawer({
  candidate,
  tab,
  onTabChange,
  onClose,
}: CandidateDrawerProps) {
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    },
    [onClose],
  )

  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown)
    const prev = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', handleKeyDown)
      document.body.style.overflow = prev
    }
  }, [handleKeyDown])

  const score = candidate.scoring?.total_score ?? 0
  const decision = candidate.decision?.decision ?? 'REJECT'
  const badge = decisionBadge(decision)
  const showOnboarding = decision === 'HIRE' && candidate.onboarding

  return (
    <>
      <div
        className="drawer-backdrop"
        onClick={onClose}
        aria-hidden="true"
      />
      <aside
        className="drawer"
        role="dialog"
        aria-modal="true"
        aria-labelledby="drawer-title"
      >
        <div className="drawer-header">
          <div>
            <h2 id="drawer-title" style={{ fontSize: 'var(--text-xl)', fontWeight: 700, marginBottom: 'var(--space-2)' }}>
              {candidate.candidate?.name ?? 'Unknown candidate'}
            </h2>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--space-3)', alignItems: 'center' }}>
              <span className={`badge ${badge.className}`}>{badge.label}</span>
              {candidate.decision?.flag_for_human_review && (
                <span className="badge badge--interview">Needs review</span>
              )}
              <span className="text-secondary" style={{ fontSize: 'var(--text-sm)' }}>
                Confidence: <strong style={{ color: 'var(--text)' }}>{candidate.decision?.confidence ?? '—'}</strong>
              </span>
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-4)' }}>
            <div style={{ textAlign: 'center' }}>
              <div className="text-tertiary" style={{ fontSize: 11, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 4 }}>
                Fit score
              </div>
              <div className={`score-ring score-ring--lg ${scoreClass(score)}`}>{score}</div>
            </div>
            <button
              type="button"
              className="icon-btn"
              onClick={onClose}
              aria-label="Close candidate details"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          </div>
        </div>

        <div className="drawer-tabs" role="tablist" aria-label="Candidate details">
          {(['overview', 'screening', 'communication'] as const).map((t) => (
            <button
              key={t}
              type="button"
              role="tab"
              aria-selected={tab === t}
              className={`tab ${tab === t ? 'tab--active' : ''}`}
              onClick={() => onTabChange(t)}
            >
              {t.charAt(0).toUpperCase() + t.slice(1)}
            </button>
          ))}
          {showOnboarding && (
            <button
              type="button"
              role="tab"
              aria-selected={tab === 'onboarding'}
              className={`tab ${tab === 'onboarding' ? 'tab--active' : ''}`}
              onClick={() => onTabChange('onboarding')}
            >
              Onboarding
            </button>
          )}
        </div>

        <div className="drawer-body" role="tabpanel">
          {tab === 'overview' && <OverviewPanel candidate={candidate} />}
          {tab === 'screening' && <ScreeningPanel candidate={candidate} />}
          {tab === 'communication' && <CommunicationPanel candidate={candidate} />}
          {tab === 'onboarding' && showOnboarding && (
            <OnboardingPanel onboarding={candidate.onboarding!} />
          )}
        </div>
      </aside>
    </>
  )
}

function OverviewPanel({ candidate }: { candidate: RecruitResult }) {
  const scores = [
    { label: 'Skills', val: candidate.scoring?.skills_score ?? 0 },
    { label: 'Experience', val: candidate.scoring?.experience_score ?? 0 },
    { label: 'Education', val: candidate.scoring?.education_score ?? 0 },
  ]

  return (
    <div className="stack stack--lg">
      <div className="stat-grid">
        {scores.map((s) => (
          <div key={s.label} className="stat-card">
            <div className={`stat-card__value ${scoreClass(s.val)}`}>{s.val}</div>
            <div className="stat-card__label">{s.label}</div>
          </div>
        ))}
      </div>

      {candidate.scoring?.scoring_reasoning && (
        <div>
          <h3 className="section-title">Scoring rationale</h3>
          <p style={{ fontSize: 'var(--text-sm)', lineHeight: 'var(--leading-relaxed)', fontStyle: 'italic' }}>
            {candidate.scoring.scoring_reasoning}
          </p>
        </div>
      )}

      <div className="split-columns">
        <div>
          <h3 className="section-title" style={{ color: 'var(--success)' }}>Strengths</h3>
          <ul style={{ paddingLeft: 20, margin: 0, fontSize: 'var(--text-sm)' }}>
            {(candidate.scoring?.strengths ?? []).map((s, i) => (
              <li key={i} style={{ marginBottom: 8 }}>{s}</li>
            ))}
          </ul>
        </div>
        <div>
          <h3 className="section-title" style={{ color: 'var(--warning)' }}>Gaps</h3>
          <ul style={{ paddingLeft: 20, margin: 0, fontSize: 'var(--text-sm)', color: 'var(--text-secondary)' }}>
            {(candidate.scoring?.weaknesses ?? []).map((w, i) => (
              <li key={i} style={{ marginBottom: 8 }}>{w}</li>
            ))}
          </ul>
        </div>
      </div>

      {(candidate.candidate?.skills?.length ?? 0) > 0 && (
        <div>
          <h3 className="section-title">Skills extracted</h3>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            {candidate.candidate!.skills.map((skill, i) => (
              <span key={i} className="chip">{skill}</span>
            ))}
          </div>
        </div>
      )}

      {candidate.decision?.decision_reasoning && (
        <div>
          <h3 className="section-title">Decision</h3>
          <p className="text-secondary" style={{ fontSize: 'var(--text-sm)' }}>
            {candidate.decision.decision_reasoning}
          </p>
        </div>
      )}

      {candidate.decision?.salary_recommendation && (
        <div className="card card--flat card__body--compact">
          <span className="text-tertiary" style={{ fontSize: 'var(--text-xs)' }}>Salary recommendation</span>
          <div style={{ fontWeight: 600, marginTop: 4 }}>{candidate.decision.salary_recommendation}</div>
        </div>
      )}

      {['INTERVIEW', 'HIRE'].includes(candidate.decision?.decision ?? '') &&
        (candidate.decision?.suggested_interview_questions?.length ?? 0) > 0 && (
          <div>
            <h3 className="section-title">Suggested interview questions</h3>
            <ol style={{ paddingLeft: 20, margin: 0, fontSize: 'var(--text-sm)' }}>
              {candidate.decision!.suggested_interview_questions.map((q, i) => (
                <li key={i} style={{ marginBottom: 12, lineHeight: 'var(--leading-relaxed)' }}>{q}</li>
              ))}
            </ol>
          </div>
        )}
    </div>
  )
}

function ScreeningPanel({ candidate }: { candidate: RecruitResult }) {
  const pct = candidate.screening?.skills_match_percentage ?? 0

  return (
    <div className="stack stack--lg">
      <div className="card card__body--compact">
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
          <span style={{ fontWeight: 600, fontSize: 'var(--text-sm)' }}>Skills match</span>
          <span className={scoreClass(pct)} style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>
            {pct}%
          </span>
        </div>
        <div className="progress-track">
          <div
            className="progress-fill"
            style={{ width: `${pct}%`, background: 'var(--accent)' }}
          />
        </div>

        <div className="split-columns" style={{ marginTop: 24 }}>
          <MatchRow label="Experience requirement" match={candidate.screening?.experience_match} />
          <MatchRow label="Education requirement" match={candidate.screening?.education_match} />
        </div>
      </div>

      {candidate.screening?.screening_notes && (
        <div>
          <h3 className="section-title">Notes</h3>
          <p className="text-secondary" style={{ fontSize: 'var(--text-sm)' }}>
            {candidate.screening.screening_notes}
          </p>
        </div>
      )}

      <div className="split-columns">
        <div>
          <h3 className="section-title" style={{ color: 'var(--success)' }}>Requirements met</h3>
          <ul style={{ paddingLeft: 20, margin: 0, fontSize: 'var(--text-sm)' }}>
            {(candidate.screening?.matches ?? []).map((m, i) => (
              <li key={i} style={{ marginBottom: 8 }}>{m}</li>
            ))}
          </ul>
        </div>
        <div>
          <h3 className="section-title" style={{ color: 'var(--warning)' }}>Gaps identified</h3>
          <ul style={{ paddingLeft: 20, margin: 0, fontSize: 'var(--text-sm)', color: 'var(--text-secondary)' }}>
            {(candidate.screening?.gaps ?? []).map((g, i) => (
              <li key={i} style={{ marginBottom: 8 }}>{g}</li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  )
}

function MatchRow({ label, match }: { label: string; match?: boolean }) {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: 12,
        background: 'var(--surface-inset)',
        borderRadius: 'var(--radius-md)',
        fontSize: 'var(--text-sm)',
      }}
    >
      <span>{label}</span>
      {match ? (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--success)" strokeWidth="2" aria-label="Met">
          <polyline points="20 6 9 17 4 12" />
        </svg>
      ) : (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--danger)" strokeWidth="2" aria-label="Not met">
          <line x1="18" y1="6" x2="6" y2="18" />
          <line x1="6" y1="6" x2="18" y2="18" />
        </svg>
      )}
    </div>
  )
}

function CommunicationPanel({ candidate }: { candidate: RecruitResult }) {
  return (
    <div className="stack">
      <div className="card card--flat card__body--compact">
        <div className="text-tertiary" style={{ fontSize: 11, fontWeight: 600, textTransform: 'uppercase', marginBottom: 4 }}>
          Email type
        </div>
        <div style={{ fontWeight: 600 }}>{candidate.communication?.email_type ?? 'Draft'}</div>
      </div>
      <div className="card card__body markdown-body">
        <ReactMarkdown>
          {candidate.communication?.email_content ?? 'No email content generated.'}
        </ReactMarkdown>
      </div>
    </div>
  )
}

function OnboardingPanel({
  onboarding,
}: {
  onboarding: NonNullable<RecruitResult['onboarding']>
}) {
  return (
    <div className="stack stack--lg">
      <div className="banner banner--success" role="status">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
          <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
          <polyline points="22 4 12 14.01 9 11.01" />
        </svg>
        <span>Hire decision — onboarding package generated automatically.</span>
      </div>

      <section>
        <h3 className="section-title">Documents</h3>
        {(onboarding.documents_generated ?? []).map((doc, i) => (
          <div key={i} className="card card__body markdown-body" style={{ marginBottom: 16 }}>
            <ReactMarkdown>{doc}</ReactMarkdown>
          </div>
        ))}
      </section>

      <section>
        <h3 className="section-title">Training plan</h3>
        <div className="card card__body markdown-body">
          <ReactMarkdown>{onboarding.training_plan ?? ''}</ReactMarkdown>
        </div>
      </section>

      <section>
        <h3 className="section-title">Welcome email</h3>
        <div className="card card__body markdown-body">
          <ReactMarkdown>{onboarding.email_draft ?? ''}</ReactMarkdown>
        </div>
      </section>
    </div>
  )
}
