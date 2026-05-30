import { Link } from 'react-router-dom'
import AppLayout from '../components/AppLayout'

const FEATURES = [
  {
    title: 'Batch resume screening',
    desc: 'Upload multiple PDFs and compare candidates ranked by fit score against your job description.',
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
        <polyline points="14 2 14 8 20 8" />
      </svg>
    ),
  },
  {
    title: 'Structured hiring decisions',
    desc: 'Every candidate gets a Hire, Interview, or Reject recommendation with reasoning and interview questions.',
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
        <polyline points="22 4 12 14.01 9 11.01" />
      </svg>
    ),
  },
  {
    title: 'Instant onboarding packages',
    desc: 'Hire decisions trigger offer documents, 30-60-90 training plans, and welcome emails in one flow.',
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <rect x="3" y="4" width="18" height="18" rx="2" />
        <line x1="16" y1="2" x2="16" y2="6" />
        <line x1="8" y1="2" x2="8" y2="6" />
        <line x1="3" y1="10" x2="21" y2="10" />
      </svg>
    ),
  },
]

export default function Landing() {
  return (
    <AppLayout>
      <section className="landing-hero container">
        <p className="landing-hero__eyebrow">
          <span
            style={{
              width: 6,
              height: 6,
              borderRadius: '50%',
              background: 'var(--success)',
            }}
            aria-hidden="true"
          />
          AI recruitment pipeline
        </p>
        <h1 className="landing-hero__title">
          Hire and onboard without the busywork.
        </h1>
        <p className="landing-hero__subtitle">
          SmartOnboard runs your resumes through screening, scoring, and decision agents —
          then generates onboarding artifacts for every hire. Built for HR teams who need
          speed without sacrificing rigor.
        </p>
        <div className="landing-hero__actions">
          <Link to="/register" className="btn btn--primary btn--lg">
            Create your workspace
          </Link>
          <a href="#how-it-works" className="btn btn--secondary btn--lg">
            See how it works
          </a>
        </div>
      </section>

      <section id="how-it-works" className="container landing-split">
        <div>
          <h2 style={{ fontSize: 'var(--text-3xl)', fontWeight: 700, letterSpacing: '-0.02em', marginBottom: 'var(--space-4)' }}>
            One pipeline from resume to offer
          </h2>
          <p className="text-secondary" style={{ fontSize: 'var(--text-lg)', lineHeight: 'var(--leading-relaxed)', marginBottom: 'var(--space-8)' }}>
            Drop in job details and resumes. The system parses, screens, scores, drafts
            communication, and prepares onboarding — so your team reviews outcomes, not spreadsheets.
          </p>
          <div className="feature-list">
            {FEATURES.map((f) => (
              <div key={f.title} className="feature-item">
                <div className="feature-item__icon" aria-hidden="true">{f.icon}</div>
                <div>
                  <div className="feature-item__title">{f.title}</div>
                  <p className="feature-item__desc">{f.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="pipeline-preview" aria-hidden="true">
          <div className="pipeline-preview__line">$ smartonboard run --role &quot;Senior Engineer&quot;</div>
          <div className="pipeline-preview__line pipeline-preview__line--active">→ Parsing resume...</div>
          <div className="pipeline-preview__line pipeline-preview__line--active">→ Screening against JD</div>
          <div className="pipeline-preview__line">→ Scoring fit (84/100)</div>
          <div className="pipeline-preview__line">→ Decision: INTERVIEW</div>
          <div className="pipeline-preview__line">
            <span className="pipeline-preview__cursor" />
          </div>
        </div>
      </section>

      <section className="container metrics-row" aria-label="Product capabilities">
        <div className="metric">
          <div className="metric__value">5</div>
          <div className="metric__label">AI agents per candidate</div>
        </div>
        <div className="metric">
          <div className="metric__value">PDF</div>
          <div className="metric__label">Batch upload supported</div>
        </div>
        <div className="metric">
          <div className="metric__value">1-click</div>
          <div className="metric__label">Full candidate dossier</div>
        </div>
      </section>

      <section
        className="container"
        style={{
          padding: 'var(--space-12) 0 var(--space-20)',
          textAlign: 'center',
          borderTop: '1px solid var(--border)',
        }}
      >
        <h2 style={{ fontSize: 'var(--text-2xl)', fontWeight: 700, marginBottom: 'var(--space-3)' }}>
          Ready to run your first pipeline?
        </h2>
        <p className="text-secondary" style={{ marginBottom: 'var(--space-6)', maxWidth: 420, marginInline: 'auto' }}>
          Upload resumes, add a job description, and get ranked results in minutes.
        </p>
        <Link to="/dashboard" className="btn btn--accent btn--lg">
          Open HR dashboard
        </Link>
      </section>
    </AppLayout>
  )
}
