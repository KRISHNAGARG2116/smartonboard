import { Link } from 'react-router-dom'

export default function Landing() {
  const handleScrollTo = (e: React.MouseEvent<HTMLAnchorElement>, id: string) => {
    e.preventDefault()
    const element = document.getElementById(id)
    if (element) {
      element.scrollIntoView({ behavior: 'smooth' })
    }
  }

  return (
    <div style={{
      minHeight: '100vh',
      background: 'var(--bg)',
      color: 'var(--text)',
      fontFamily: "var(--font-sans)",
      overflowX: 'hidden'
    }}>
      {/* Top Navbar */}
      <header style={{
        position: 'sticky',
        top: 0,
        zIndex: 100,
        height: 'var(--header-h)',
        background: 'var(--bg)',
        borderBottom: '1px solid var(--border)',
      }}>
        <div style={{
          maxWidth: 1200,
          margin: '0 auto',
          padding: '0 var(--space-6)',
          height: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 'var(--space-4)',
        }}>
          {/* Logo */}
          <Link to="/" style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)', fontWeight: 500, fontSize: 'var(--text-lg)', letterSpacing: '0.04em', color: 'var(--text)', textDecoration: 'none' }}>
            SmartOnboard
          </Link>

          {/* Nav Links */}
          <nav style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
            <a href="#features" onClick={(e) => handleScrollTo(e, 'features')} className="nav-link" style={{ cursor: 'pointer' }}>
              Features
            </a>
            <a href="#solutions" onClick={(e) => handleScrollTo(e, 'solutions')} className="nav-link" style={{ cursor: 'pointer' }}>
              Solutions
            </a>
            <a href="#pricing" onClick={(e) => handleScrollTo(e, 'pricing')} className="nav-link" style={{ cursor: 'pointer' }}>
              Pricing
            </a>
            <a href="#about" onClick={(e) => handleScrollTo(e, 'about')} className="nav-link" style={{ cursor: 'pointer' }}>
              About
            </a>
          </nav>

          {/* Auth Actions */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
            <Link to="/login" className="btn btn--secondary btn--sm" style={{ cursor: 'pointer' }}>
              Login
            </Link>
            <Link to="/register" className="btn btn--primary btn--sm" style={{ cursor: 'pointer', background: 'var(--color-dark-cork)' }}>
              Register
            </Link>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section style={{
        minHeight: 'calc(80vh - var(--header-h))',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'center',
        textAlign: 'center',
        padding: 'var(--space-16) var(--space-6)',
        maxWidth: 900,
        margin: '0 auto',
      }}>
        <span style={{
          fontSize: 10,
          fontWeight: 500,
          color: 'var(--color-burnt-sienna)',
          letterSpacing: '0.1em',
          textTransform: 'uppercase',
          marginBottom: 'var(--space-4)'
        }}>
          Verified Hiring Operating System
        </span>
        
        <h1 style={{
          fontSize: 'var(--text-5xl)',
          fontWeight: 500,
          lineHeight: 'var(--leading-tight)',
          letterSpacing: '-0.02em',
          color: 'var(--text)',
          margin: 'var(--space-2) 0 var(--space-4)',
          maxWidth: '20ch'
        }}>
          AI-Powered Hiring & Candidate Management
        </h1>

        <p style={{
          fontSize: 'var(--text-lg)',
          lineHeight: 'var(--leading-normal)',
          color: 'var(--text-secondary)',
          maxWidth: 600,
          margin: '0 0 var(--space-8)'
        }}>
          Screen resumes, match candidates, manage interviews, and streamline hiring workflows from one platform.
        </p>

        {/* Hero CTAs */}
        <div style={{ display: 'flex', gap: 'var(--space-4)', justifyContent: 'center' }}>
          <Link to="/register" className="btn btn--primary btn--lg" style={{ background: 'var(--color-dark-cork)', color: 'var(--color-warm-cream)' }}>
            Get Started
          </Link>
          <a href="#features" onClick={(e) => handleScrollTo(e, 'features')} className="btn btn--secondary btn--lg">
            Learn More
          </a>
        </div>
      </section>

      {/* Social Proof / Candidate Lifecycle Progress Section */}
      <section style={{
        borderTop: '1px solid var(--border)',
        borderBottom: '1px solid var(--border)',
        background: 'rgba(56, 36, 22, 0.05)',
        padding: 'var(--space-12) var(--space-6)'
      }}>
        <div style={{ maxWidth: 1200, margin: '0 auto' }}>
          <div style={{ textAlign: 'center', marginBottom: 'var(--space-8)' }}>
            <span style={{ fontSize: 10, color: 'var(--text-secondary)', letterSpacing: '0.05em', textTransform: 'uppercase' }}>
              Platform Operations
            </span>
            <h2 style={{ fontSize: 'var(--text-2xl)', fontWeight: 500, color: 'var(--text)', marginTop: 'var(--space-2)' }}>
              Candidate Lifecycle Progress
            </h2>
            <p style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)', marginTop: 'var(--space-2)' }}>
              A secure, automated journey optimized for verification, fit assessment, and placement signals.
            </p>
          </div>

          {/* Lifecycle Stepper Graphic */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))',
            gap: 'var(--space-4)',
            position: 'relative'
          }}>
            {[
              { step: '01', title: 'Resume Parsing', desc: 'Candidates upload up to 3 resumes, extracting qualifications instantly.' },
              { step: '02', title: 'AI Match Analysis', desc: 'Real-time analysis calculates the exact applicability match percentage.' },
              { step: '03', title: 'Identity Verified', desc: 'Secure Twilio SMS OTP and Email validation ensures authentic profiles.' },
              { step: '04', title: 'Cockpit Screened', desc: 'Recruiters review internal evidence, risk levels, and authenticity indicators.' },
              { step: '05', title: 'Structured Interview', desc: 'Dynamic scheduling alignment and recruiter evaluation ranking.' },
              { step: '06', title: 'Verified Placement', desc: 'Objective hiring decisions backed by trusted signal telemetry.' }
            ].map((item, idx) => (
              <div key={idx} style={{
                border: '1px solid var(--border)',
                borderRadius: 'var(--radius-cards)',
                padding: 'var(--space-4)',
                background: 'var(--bg)',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
                height: '100%'
              }}>
                <div>
                  <div style={{
                    fontSize: 'var(--text-xs)',
                    color: 'var(--color-burnt-sienna)',
                    fontWeight: 500,
                    marginBottom: 'var(--space-2)'
                  }}>
                    STEP {item.step}
                  </div>
                  <h3 style={{
                    fontSize: 'var(--text-sm)',
                    fontWeight: 500,
                    color: 'var(--text)',
                    marginBottom: 'var(--space-2)'
                  }}>
                    {item.title}
                  </h3>
                  <p style={{
                    fontSize: 'var(--text-xs)',
                    color: 'var(--text-secondary)',
                    lineHeight: 'var(--leading-caption)'
                  }}>
                    {item.desc}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Feature Section */}
      <section id="features" style={{
        padding: 'var(--space-16) var(--space-6)'
      }}>
        <div style={{ maxWidth: 1200, margin: '0 auto' }}>
          <div style={{ textAlign: 'center', marginBottom: 'var(--space-12)' }}>
            <span style={{ fontSize: 10, color: 'var(--text-secondary)', letterSpacing: '0.05em', textTransform: 'uppercase' }}>
              Core Capabilities
            </span>
            <h2 style={{ fontSize: 'var(--text-3xl)', fontWeight: 500, color: 'var(--text)', marginTop: 'var(--space-2)' }}>
              Unified Hiring Architecture
            </h2>
            <p style={{ fontSize: 'var(--text-base)', color: 'var(--text-secondary)', marginTop: 'var(--space-3)', maxWidth: 540, marginInline: 'auto' }}>
              Six pillars designed to elevate recruiter confidence, optimize match quality, and eliminate application spam.
            </p>
          </div>

          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
            gap: 'var(--space-6)'
          }}>
            {/* Feature 1 */}
            <div style={{ border: '1px solid var(--border)', borderRadius: 'var(--radius-cards)', padding: 'var(--space-6)', background: 'transparent' }}>
              <div style={{ fontSize: 24, marginBottom: 'var(--space-3)' }}>📄</div>
              <h3 style={{ fontSize: 'var(--text-lg)', fontWeight: 500, color: 'var(--text)', marginBottom: 'var(--space-3)' }}>
                AI Resume Screening
              </h3>
              <p style={{ fontSize: 'var(--text-sm)', lineHeight: 'var(--leading-normal)', color: 'var(--text-secondary)' }}>
                Automatically parse, extract, and index key experiences from up to 3 candidate resumes, mapping them directly to target requisitions.
              </p>
            </div>

            {/* Feature 2 */}
            <div style={{ border: '1px solid var(--border)', borderRadius: 'var(--radius-cards)', padding: 'var(--space-6)', background: 'transparent' }}>
              <div style={{ fontSize: 24, marginBottom: 'var(--space-3)' }}>🎯</div>
              <h3 style={{ fontSize: 'var(--text-lg)', fontWeight: 500, color: 'var(--text)', marginBottom: 'var(--space-3)' }}>
                Candidate Matching
              </h3>
              <p style={{ fontSize: 'var(--text-sm)', lineHeight: 'var(--leading-normal)', color: 'var(--text-secondary)' }}>
                Get instant scoring visibility. Compare required vs missing skills transparently so you know exactly how each candidate matches.
              </p>
            </div>

            {/* Feature 3 */}
            <div style={{ border: '1px solid var(--border)', borderRadius: 'var(--radius-cards)', padding: 'var(--space-6)', background: 'transparent' }}>
              <div style={{ fontSize: 24, marginBottom: 'var(--space-3)' }}>📊</div>
              <h3 style={{ fontSize: 'var(--text-lg)', fontWeight: 500, color: 'var(--text)', marginBottom: 'var(--space-3)' }}>
                Sourcing Pipelines
              </h3>
              <p style={{ fontSize: 'var(--text-sm)', lineHeight: 'var(--leading-normal)', color: 'var(--text-secondary)' }}>
                Coordinate applicant reviews with drag-and-drop sourcing pipelines. Drag verified candidates from application to final offer seamlessly.
              </p>
            </div>

            {/* Feature 4 */}
            <div style={{ border: '1px solid var(--border)', borderRadius: 'var(--radius-cards)', padding: 'var(--space-6)', background: 'transparent' }}>
              <div style={{ fontSize: 24, marginBottom: 'var(--space-3)' }}>📅</div>
              <h3 style={{ fontSize: 'var(--text-lg)', fontWeight: 500, color: 'var(--text)', marginBottom: 'var(--space-3)' }}>
                Interview Scheduling
              </h3>
              <p style={{ fontSize: 'var(--text-sm)', lineHeight: 'var(--leading-normal)', color: 'var(--text-secondary)' }}>
                Accelerate hiring loops with a centralized scheduling cockpit. Manage time slots, coordinate panel notes, and queue candidate pools.
              </p>
            </div>

            {/* Feature 5 */}
            <div style={{ border: '1px solid var(--border)', borderRadius: 'var(--radius-cards)', padding: 'var(--space-6)', background: 'transparent' }}>
              <div style={{ fontSize: 24, marginBottom: 'var(--space-3)' }}>🛡️</div>
              <h3 style={{ fontSize: 'var(--text-lg)', fontWeight: 500, color: 'var(--text)', marginBottom: 'var(--space-3)' }}>
                Candidate Verification
              </h3>
              <p style={{ fontSize: 'var(--text-sm)', lineHeight: 'var(--leading-normal)', color: 'var(--text-secondary)' }}>
                Eliminate ghost candidates and application noise. Authenticate profiles utilizing mandatory Email and Twilio SMS OTP gateway checks.
              </p>
            </div>

            {/* Feature 6 */}
            <div style={{ border: '1px solid var(--border)', borderRadius: 'var(--radius-cards)', padding: 'var(--space-6)', background: 'transparent' }}>
              <div style={{ fontSize: 24, marginBottom: 'var(--space-3)' }}>📈</div>
              <h3 style={{ fontSize: 'var(--text-lg)', fontWeight: 500, color: 'var(--text)', marginBottom: 'var(--space-3)' }}>
                Recruiter Analytics
              </h3>
              <p style={{ fontSize: 'var(--text-sm)', lineHeight: 'var(--leading-normal)', color: 'var(--text-secondary)' }}>
                Empower hiring decisions with advanced metrics. Assess candidate risk ratings, authenticity quotients, and evidence-backed matching reports.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Solutions Section */}
      <section id="solutions" style={{
        borderTop: '1px dashed var(--border)',
        padding: 'var(--space-16) var(--space-6)',
        background: 'rgba(255, 237, 215, 0.01)'
      }}>
        <div style={{ maxWidth: 1200, margin: '0 auto' }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: 'var(--space-10)', alignItems: 'center' }}>
            <div>
              <span style={{ fontSize: 10, color: 'var(--color-burnt-sienna)', letterSpacing: '0.05em', textTransform: 'uppercase' }}>
                Tailored Spaces
              </span>
              <h2 style={{ fontSize: 'var(--text-3xl)', fontWeight: 500, color: 'var(--text)', marginTop: 'var(--space-2)' }}>
                Who We Serve
              </h2>
              <p style={{ fontSize: 'var(--text-base)', color: 'var(--text-secondary)', marginTop: 'var(--space-4)', lineHeight: 'var(--leading-normal)' }}>
                SmartOnboard is a closed hiring system. Whether you are scaling an executive team or seeking your next technical match, we maintain verification standards at every boundary.
              </p>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)' }}>
              {/* Recruiter Solution Card */}
              <div style={{ border: '1px solid var(--border)', padding: 'var(--space-6)', borderRadius: 'var(--radius-cards)', background: 'var(--bg)' }}>
                <h3 style={{ fontSize: 'var(--text-lg)', fontWeight: 500, color: 'var(--text)', marginBottom: 'var(--space-2)' }}>
                  Recruiters & Hiring Teams
                </h3>
                <p style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)', lineHeight: 'var(--leading-normal)', marginBottom: 'var(--space-4)' }}>
                  Take back control of your pipeline. Screen applicants objectively with AI skills verification, check security scores, and collaborate in real-time.
                </p>
                <Link to="/register" style={{ fontSize: 'var(--text-sm)', color: 'var(--color-burnt-sienna)', textDecoration: 'underline' }}>
                  Open hiring account &rarr;
                </Link>
              </div>

              {/* Candidate Solution Card */}
              <div style={{ border: '1px solid var(--border)', padding: 'var(--space-6)', borderRadius: 'var(--radius-cards)', background: 'var(--bg)' }}>
                <h3 style={{ fontSize: 'var(--text-lg)', fontWeight: 500, color: 'var(--text)', marginBottom: 'var(--space-2)' }}>
                  Candidates & Job Seekers
                </h3>
                <p style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)', lineHeight: 'var(--leading-normal)', marginBottom: 'var(--space-4)' }}>
                  Apply to jobs with transparent suitability scoring. Highlight your verified skills, manage up to 3 active resumes, and coordinate schedules directly.
                </p>
                <Link to="/register" style={{ fontSize: 'var(--text-sm)', color: 'var(--color-burnt-sienna)', textDecoration: 'underline' }}>
                  Register candidate profile &rarr;
                </Link>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Pricing Section */}
      <section id="pricing" style={{
        borderTop: '1px dashed var(--border)',
        padding: 'var(--space-16) var(--space-6)'
      }}>
        <div style={{ maxWidth: 1000, margin: '0 auto' }}>
          <div style={{ textAlign: 'center', marginBottom: 'var(--space-12)' }}>
            <span style={{ fontSize: 10, color: 'var(--text-secondary)', letterSpacing: '0.05em', textTransform: 'uppercase' }}>
              Simple Pricing
            </span>
            <h2 style={{ fontSize: 'var(--text-3xl)', fontWeight: 500, color: 'var(--text)', marginTop: 'var(--space-2)' }}>
              Transparent Plans. No Hidden Costs.
            </h2>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 'var(--space-6)' }}>
            {/* Candidate Plan */}
            <div style={{ border: '1px solid var(--border)', borderRadius: 'var(--radius-cards)', padding: 'var(--space-8)', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', minHeight: 320 }}>
              <div>
                <h3 style={{ fontSize: 'var(--text-xl)', fontWeight: 500, color: 'var(--text)' }}>
                  Job Seekers
                </h3>
                <div style={{ display: 'flex', alignItems: 'baseline', margin: 'var(--space-4) 0' }}>
                  <span style={{ fontSize: 'var(--text-3xl)', fontWeight: 500, color: 'var(--text)' }}>Free</span>
                  <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-secondary)', marginLeft: 'var(--space-2)' }}>forever</span>
                </div>
                <p style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)', lineHeight: 'var(--leading-normal)' }}>
                  Build a verified identity, upload up to 3 resumes, and view match alignment scoring across all active roles.
                </p>
              </div>
              <Link to="/register" className="btn btn--secondary btn--block" style={{ marginTop: 'var(--space-6)' }}>
                Create Free Profile
              </Link>
            </div>

            {/* Recruiter Plan */}
            <div style={{ border: '1px solid var(--text)', borderRadius: 'var(--radius-cards)', padding: 'var(--space-8)', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', minHeight: 320, background: 'rgba(56, 36, 22, 0.2)' }}>
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <h3 style={{ fontSize: 'var(--text-xl)', fontWeight: 500, color: 'var(--text)' }}>
                    Recruiter Workspace
                  </h3>
                  <span className="badge badge--hire">Active</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'baseline', margin: 'var(--space-4) 0' }}>
                  <span style={{ fontSize: 'var(--text-3xl)', fontWeight: 500, color: 'var(--text)' }}>$49</span>
                  <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-secondary)', marginLeft: 'var(--space-2)' }}>/ month per active job</span>
                </div>
                <p style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)', lineHeight: 'var(--leading-normal)' }}>
                  Post jobs, access unlimited matching candidates, review risk/authenticity evidence metrics, and manage custom pipeline stages.
                </p>
              </div>
              <Link to="/register" className="btn btn--primary btn--block" style={{ marginTop: 'var(--space-6)', background: 'var(--color-dark-cork)', color: 'var(--color-warm-cream)' }}>
                Get Started
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* About Section */}
      <section id="about" style={{
        borderTop: '1px dashed var(--border)',
        padding: 'var(--space-16) var(--space-6)',
        background: 'rgba(56, 36, 22, 0.02)'
      }}>
        <div style={{ maxWidth: 800, margin: '0 auto', textAlign: 'center' }}>
          <span style={{ fontSize: 10, color: 'var(--text-secondary)', letterSpacing: '0.05em', textTransform: 'uppercase' }}>
            Our Philosophy
          </span>
          <h2 style={{ fontSize: 'var(--text-3xl)', fontWeight: 500, color: 'var(--text)', marginTop: 'var(--space-2)', marginBottom: 'var(--space-4)' }}>
            Trust Over Volume
          </h2>
          <p style={{ fontSize: 'var(--text-base)', color: 'var(--text-secondary)', lineHeight: 'var(--leading-normal)', marginInline: 'auto', maxWidth: 640 }}>
            SmartOnboard is built to combat the friction of application spam. We don't optimize for vanity volume. We optimize for credential verification, objective skills verification, and robust signals so that recruiters can discover matches they can trust.
          </p>
        </div>
      </section>

      {/* Footer */}
      <footer style={{
        borderTop: '1px solid var(--border)',
        padding: 'var(--space-10) var(--space-6)',
        textAlign: 'center'
      }}>
        <div style={{
          maxWidth: 1200,
          margin: '0 auto',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: 'var(--space-4)'
        }}>
          <div style={{ fontSize: 12, fontWeight: 500, letterSpacing: '0.05em' }}>
            SMARTONBOARD
          </div>
          <div style={{ fontSize: 10, color: 'var(--text-secondary)', display: 'flex', gap: 'var(--space-3)', justifyContent: 'center' }}>
            <Link to="/login">Login</Link>
            <span>&bull;</span>
            <Link to="/register">Register</Link>
            <span>&bull;</span>
            <a href="#features" onClick={(e) => handleScrollTo(e, 'features')}>Features</a>
            <span>&bull;</span>
            <a href="#solutions" onClick={(e) => handleScrollTo(e, 'solutions')}>Solutions</a>
            <span>&bull;</span>
            <a href="#pricing" onClick={(e) => handleScrollTo(e, 'pricing')}>Pricing</a>
          </div>
          <p style={{ fontSize: 10, color: 'var(--text-secondary)', marginTop: 'var(--space-2)' }}>
            &copy; 2026 SmartOnboard. All rights reserved. Built with verification integrity.
          </p>
        </div>
      </footer>
    </div>
  )
}
