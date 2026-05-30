import { Link } from 'react-router-dom';
import Header from '../components/Header';

export default function Landing() {
  return (
    <div className="landing-page">
      <div className="hero-section">
        <div className="container">
          <h1 className="hero-title">
            Onboard faster. <br />
            <span className="text-accent">Screen smarter.</span>
          </h1>
          <p className="hero-subtitle">
            SmartOnboard uses multi-agent AI to automate 3+ hours of paperwork per hire.
            Get precise candidate screening and instant personalized onboarding documents.
          </p>
          <div className="flex-center" style={{ gap: '16px' }}>
            <Link to="/dashboard" className="btn btn-primary" style={{ padding: '16px 32px', fontSize: '18px' }}>
              Launch HR Dashboard
            </Link>
            <Link to="/candidate" className="btn btn-secondary" style={{ padding: '16px 32px', fontSize: '18px' }}>
              Try Candidate Portal
            </Link>
          </div>
        </div>
      </div>

      <div style={{ backgroundColor: 'var(--bg-panel)', padding: '80px 0', borderTop: '1px solid var(--border)', borderBottom: '1px solid var(--border)' }}>
        <div className="container grid-2">
          <div>
            <h2 style={{ fontSize: '36px', marginBottom: '16px' }}>Zero manual paperwork.</h2>
            <p className="text-muted" style={{ fontSize: '18px', lineHeight: 1.6 }}>
              Our AI agents draft offer letters, summarize policies, and build 30-60-90 day training plans customized for every single role and department.
            </p>
          </div>
          <div>
            <div className="card" style={{ padding: '24px' }}>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: '14px', color: 'var(--accent)', marginBottom: '16px' }}>
                $ generate_offer --role="Senior Engineer"
              </div>
              <p style={{ color: 'var(--text-muted)', fontSize: '14px' }}>Processing context...</p>
              <div style={{ height: '4px', background: 'var(--bg-dark)', borderRadius: '2px', marginTop: '8px', overflow: 'hidden' }}>
                <div style={{ height: '100%', width: '100%', background: 'var(--accent)' }}></div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="container" style={{ padding: '80px 24px', textAlign: 'center' }}>
        <h2 style={{ fontSize: '32px', marginBottom: '48px' }}>Trusted by enterprise HR teams</h2>
        <div style={{ display: 'flex', justifyContent: 'center', gap: '64px', flexWrap: 'wrap' }}>
          <div>
            <div style={{ fontSize: '48px', fontWeight: 700, color: 'var(--accent)' }}>50k+</div>
            <div className="text-muted" style={{ fontWeight: 600, textTransform: 'uppercase', letterSpacing: '1px', fontSize: '12px' }}>Hires Processed</div>
          </div>
          <div>
            <div style={{ fontSize: '48px', fontWeight: 700, color: 'var(--accent)' }}>3.5h</div>
            <div className="text-muted" style={{ fontWeight: 600, textTransform: 'uppercase', letterSpacing: '1px', fontSize: '12px' }}>Saved per hire</div>
          </div>
          <div>
            <div style={{ fontSize: '48px', fontWeight: 700, color: 'var(--accent)' }}>99%</div>
            <div className="text-muted" style={{ fontWeight: 600, textTransform: 'uppercase', letterSpacing: '1px', fontSize: '12px' }}>Compliance Rate</div>
          </div>
        </div>
      </div>
    </div>
  );
}
