import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { fetchJobs } from '../api'
import AnimatedCounter from '../components/AnimatedCounter'

export default function Landing() {
  const [activeJobsCount, setActiveJobsCount] = useState(0)

  useEffect(() => {
    fetchJobs('open')
      .then((data) => setActiveJobsCount(data.length))
      .catch(() => setActiveJobsCount(0))
  }, [])

  const handleScrollTo = (e: React.MouseEvent<HTMLAnchorElement>, id: string) => {
    e.preventDefault()
    const element = document.getElementById(id)
    if (element) {
      element.scrollIntoView({ behavior: 'smooth' })
    }
  }

  const headlineWords = "AI analytics for faster insights and zero hiring chaos".split(' ')

  return (
    <div style={{
      minHeight: '100vh',
      background: 'var(--bg)',
      color: 'var(--text)',
      fontFamily: "var(--font-sans)",
      overflowX: 'hidden',
      position: 'relative'
    }}>
      {/* Background Decorative Parallax Blobs (Mesh Gradient) */}
      <div style={{ position: 'absolute', inset: 0, overflow: 'hidden', pointerEvents: 'none', zIndex: 0 }}>
        <motion.div
          animate={{
            y: [0, -20, 0],
            x: [0, 15, 0],
            scale: [1, 1.05, 1]
          }}
          transition={{
            duration: 12,
            repeat: Infinity,
            ease: "easeInOut"
          }}
          style={{
            position: 'absolute',
            top: '5%',
            left: '15%',
            width: '450px',
            height: '450px',
            background: 'var(--color-sky-wash)',
            filter: 'blur(130px)',
            opacity: 0.22,
            borderRadius: '50%'
          }}
        />
        <motion.div
          animate={{
            y: [0, 25, 0],
            x: [0, -20, 0],
            scale: [1, 1.08, 1]
          }}
          transition={{
            duration: 15,
            repeat: Infinity,
            ease: "easeInOut"
          }}
          style={{
            position: 'absolute',
            top: '35%',
            right: '12%',
            width: '500px',
            height: '500px',
            background: 'var(--color-apricot-wash)',
            filter: 'blur(150px)',
            opacity: 0.2,
            borderRadius: '50%'
          }}
        />
      </div>

      {/* Top Navbar */}
      <header style={{
        position: 'sticky',
        top: 0,
        zIndex: 100,
        height: 'var(--header-h)',
        background: 'var(--bg)',
        borderBottom: '1px solid var(--color-cork-shadow)',
        backdropFilter: 'blur(12px)'
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
          position: 'relative',
          zIndex: 1
        }}>
          {/* Logo */}
          <Link to="/" style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)', fontWeight: 500, fontSize: 'var(--text-body-lg)', letterSpacing: '-0.02em', color: 'var(--text)', textDecoration: 'none' }}>
            <span style={{ width: '24px', height: '24px', borderRadius: '6px', background: 'var(--color-rust)', display: 'inline-block' }} />
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
            <Link to="/login" className="btn btn--secondary btn--sm" style={{ cursor: 'pointer', padding: '8px 16px', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Login
            </Link>
            <Link to="/register" className="btn btn--primary btn--sm" style={{ cursor: 'pointer', background: 'var(--color-ink)', color: 'var(--color-pure-white)', padding: '8px 16px', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Register
            </Link>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <motion.section
        initial={{ opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
        style={{
          minHeight: 'calc(65vh - var(--header-h))',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          alignItems: 'center',
          textAlign: 'center',
          padding: 'var(--space-16) var(--space-6)',
          maxWidth: 900,
          margin: '0 auto',
          position: 'relative',
          zIndex: 1
        }}
      >
        <motion.span 
          initial={{ opacity: 0, y: 5 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1, duration: 0.3 }}
          style={{
            fontSize: 10,
            fontWeight: 500,
            color: 'var(--color-rust)',
            letterSpacing: '0.12em',
            textTransform: 'uppercase',
            marginBottom: 'var(--space-4)'
          }}
        >
          Verified Hiring Ecosystem
        </motion.span>
        
        <h1 style={{
          fontFamily: 'var(--font-signifier)',
          fontSize: 'var(--text-heading-lg)',
          fontWeight: 400,
          lineHeight: 1.05,
          letterSpacing: '-0.03em',
          color: 'var(--text)',
          margin: 'var(--space-2) 0 var(--space-4)',
          maxWidth: '22ch'
        }}>
          {headlineWords.map((word, i) => (
            <motion.span
              key={i}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{
                duration: 0.3,
                delay: i * 0.04,
                ease: [0.16, 1, 0.3, 1]
              }}
              style={{ display: 'inline-block', marginRight: '0.22em' }}
            >
              {i === 6 ? <em style={{ fontStyle: 'italic', fontFamily: 'var(--font-signifier)' }}>{word}</em> : word}
            </motion.span>
          ))}
        </h1>

        <motion.p 
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.4, duration: 0.3 }}
          style={{
            fontSize: 'var(--text-body-lg)',
            lineHeight: 1.4,
            color: 'var(--color-ash)',
            maxWidth: 600,
            margin: '0 0 var(--space-8)'
          }}
        >
          Built to maximize recruiter trust and candidate fit. Screen resumes, verify candidates with OTP, and make confident placement decisions.
        </motion.p>

        {/* Hero CTAs */}
        <motion.div 
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5, duration: 0.3 }}
          style={{ display: 'flex', gap: 'var(--space-4)', justifyContent: 'center' }}
        >
          <motion.div whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}>
            <Link to="/register" className="btn btn--primary btn--lg" style={{ background: 'var(--color-ink)', color: 'var(--color-pure-white)', borderRadius: 'var(--radius-buttons)' }}>
              Get Started
            </Link>
          </motion.div>
          <motion.div whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}>
            <a href="#features" onClick={(e) => handleScrollTo(e, 'features')} className="btn btn--secondary btn--lg" style={{ borderRadius: 'var(--radius-buttons)' }}>
              Learn More
            </a>
          </motion.div>
        </motion.div>
      </motion.section>

      {/* Workflow Story Section */}
      <section style={{
        maxWidth: 1200,
        margin: '0 auto var(--spacing-64)',
        padding: '0 var(--space-6)',
        position: 'relative',
        zIndex: 1
      }}>
        <div style={{ textAlign: 'center', marginBottom: 'var(--space-12)' }}>
          <span style={{ fontSize: 10, color: 'var(--color-rust)', letterSpacing: '0.12em', textTransform: 'uppercase', fontWeight: 600 }}>The SmartOnboard Loop</span>
          <h2 style={{ fontSize: 'var(--text-heading-sm)', fontWeight: 500, color: 'var(--text)', marginTop: 'var(--space-2)', fontFamily: 'var(--font-signifier)', letterSpacing: '-0.02em' }}>
            Unified Sourcing & Verification Sequence
          </h2>
        </div>

        {/* Visual Workflow Steps */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(6, 1fr)', gap: '12px', position: 'relative' }} className="workflow-grid">
          {[
            { step: '01', title: 'Candidate Upload', icon: '📄', desc: 'Up to 3 CV files' },
            { step: '02', title: 'AI Extraction', icon: '🤖', desc: 'Skills & experience' },
            { step: '03', title: 'OTP Verification', icon: '🛡️', desc: 'Twilio SMS & Email' },
            { step: '04', title: 'Recruiter Review', icon: '🔎', desc: 'Command center' },
            { step: '05', title: 'Interview Panel', icon: '🗓️', desc: 'Central coordinator' },
            { step: '06', title: 'Offer Locked', icon: '🎉', desc: 'Verified placement' }
          ].map((item, idx) => (
            <motion.div
              key={idx}
              initial={{ opacity: 0, y: 15 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.35, delay: idx * 0.06 }}
              className="card"
              style={{
                padding: 'var(--space-4)',
                textAlign: 'center',
                background: 'var(--surface-card)',
                borderRadius: '16px',
                border: '1px solid var(--border)',
                boxShadow: 'var(--shadow-subtle)',
                position: 'relative'
              }}
            >
              <div style={{ fontSize: '10px', fontWeight: 600, color: 'var(--color-rust)', marginBottom: '8px' }}>{item.step}</div>
              <div style={{ fontSize: '24px', marginBottom: '10px' }}>{item.icon}</div>
              <h4 style={{ fontSize: '13px', fontWeight: 500, color: 'var(--text)', marginBottom: '4px', lineHeight: 1.2 }}>{item.title}</h4>
              <p style={{ fontSize: '10px', color: 'var(--color-graphite)', margin: 0, lineHeight: 1.3 }}>{item.desc}</p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* Candidate Verification Engine */}
      <section id="verification-engine" style={{
        background: 'var(--surface-fog)',
        borderTop: '1px solid var(--border)',
        borderBottom: '1px solid var(--border)',
        padding: 'var(--spacing-96) 0',
        position: 'relative',
        zIndex: 1
      }}>
        <div style={{ maxWidth: 1200, margin: '0 auto', padding: '0 var(--space-6)' }}>
          <div style={{ display: 'grid', gridTemplateColumns: '0.8fr 1.2fr', gap: 'var(--space-12)', alignItems: 'center' }}>
            <div>
              <span style={{ fontSize: 10, color: 'var(--color-rust)', letterSpacing: '0.12em', textTransform: 'uppercase', fontWeight: 600 }}>Zero Application Spam</span>
              <h2 style={{ fontSize: 'var(--text-heading)', fontWeight: 400, color: 'var(--text)', marginTop: 'var(--space-2)', fontFamily: 'var(--font-signifier)', lineHeight: 1.1, letterSpacing: '-0.020em' }}>
                Candidate Verification Engine
              </h2>
              <p style={{ fontSize: 'var(--text-body)', color: 'var(--color-ash)', marginTop: 'var(--space-6)', lineHeight: 1.45 }}>
                Ensure applicant legitimacy at the front door. We replace vanity applicant volume with concrete trust signals, forcing verification before recruiters review portfolios.
              </p>
              <ul style={{ paddingLeft: '18px', marginTop: 'var(--space-6)', display: 'flex', flexDirection: 'column', gap: '10px', fontSize: 'var(--text-caption)', color: 'var(--color-ash)' }}>
                <li>📄 <strong>Resume Upload Cap:</strong> Candidates are limited to 3 targeted CVs to reduce scattershot applications.</li>
                <li>🤖 <strong>AI Skill Indexing:</strong> Automated extraction cross-references resume claims to build fit profiles.</li>
                <li>🛡️ <strong>SMS & Email OTP Gates:</strong> Mandatory Twilio OTP verification blocks bots and ghost profiles.</li>
                <li>📈 <strong>Identity Confidence Level:</strong> Direct verification score mapping keeps pipeline telemetry authentic.</li>
              </ul>
            </div>

            {/* Interactive Candidate Engine Mockup */}
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
              className="card"
              style={{
                background: 'var(--surface-card)',
                borderRadius: '24px',
                border: '1px solid var(--border)',
                padding: '24px',
                boxShadow: 'var(--shadow-subtle)',
                display: 'flex',
                flexDirection: 'column',
                gap: '16px'
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border)', paddingBottom: '12px' }}>
                <span style={{ fontSize: '11px', fontWeight: 600, color: 'var(--color-rust)', letterSpacing: '0.08em', textTransform: 'uppercase' }}>Candidate Workspace Preview</span>
                <span className="badge badge--hire" style={{ fontSize: '9px' }}>Profile: 100% Verified</span>
              </div>

              {/* Upload block */}
              <div style={{ padding: '14px', borderRadius: '12px', border: '1px dashed var(--border)', background: 'var(--surface-fog)', textAlign: 'center' }}>
                <div style={{ fontSize: '18px', marginBottom: '4px' }}>📄</div>
                <div style={{ fontSize: '12px', fontWeight: 500 }}>active_resume_frontend.pdf</div>
                <div style={{ fontSize: '10px', color: 'var(--color-graphite)', marginTop: '2px' }}>Resume 1 of 3 uploaded &bull; Verified 94% Skills Fit</div>
              </div>

              {/* Extracted skills block */}
              <div>
                <div style={{ fontSize: '10px', fontWeight: 600, textTransform: 'uppercase', color: 'var(--color-graphite)', marginBottom: '8px' }}>Extracted Skill Matrix</div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                  {['React', 'TypeScript', 'Node.js', 'PostgreSQL', 'Git'].map(s => (
                    <span key={s} className="badge badge--neutral" style={{ fontSize: '9px', padding: '3px 8px' }}>✓ {s}</span>
                  ))}
                  <span className="badge badge--reject" style={{ fontSize: '9px', padding: '3px 8px' }}>✕ Kubernetes</span>
                </div>
              </div>

              {/* Verification checks block */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {[
                  { label: 'Email Verification OTP Gate', status: 'VERIFIED', active: true },
                  { label: 'Twilio Phone SMS OTP Gateway', status: 'VERIFIED', active: true },
                  { label: 'Organizational Fit Scorer', status: '94% COMPATIBLE', active: false }
                ].map((item, idx) => (
                  <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'var(--surface-fog)', padding: '10px 14px', borderRadius: '8px', fontSize: '11.5px' }}>
                    <span style={{ color: 'var(--text-secondary)' }}>{item.label}</span>
                    <span style={{ fontSize: '9.5px', fontWeight: 600, color: item.active ? 'var(--success)' : 'var(--color-rust)' }}>{item.status}</span>
                  </div>
                ))}
              </div>
            </motion.div>
          </div>
        </div>
      </section>

      {/* Recruiter Command Center */}
      <section id="command-center" style={{
        padding: 'var(--spacing-96) 0',
        position: 'relative',
        zIndex: 1
      }}>
        <div style={{ maxWidth: 1200, margin: '0 auto', padding: '0 var(--space-6)' }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 0.8fr', gap: 'var(--space-12)', alignItems: 'center' }}>
            {/* Interactive Recruiter Dashboard Preview */}
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
              className="card"
              style={{
                background: 'var(--surface-card)',
                borderRadius: '24px',
                border: '1px solid var(--border)',
                padding: '24px',
                boxShadow: 'var(--shadow-subtle)',
                display: 'flex',
                flexDirection: 'column',
                gap: '16px'
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border)', paddingBottom: '12px' }}>
                <div>
                  <span style={{ fontSize: '11px', fontWeight: 600, color: 'var(--color-rust)', letterSpacing: '0.08em', textTransform: 'uppercase' }}>Hiring Control Cockpit</span>
                  <div style={{ fontSize: '12px', color: 'var(--color-graphite)', marginTop: '2px' }}>Active Job: Lead React Architect</div>
                </div>
                <span className="badge badge--interview" style={{ fontSize: '9px' }}>AI Queue: Active</span>
              </div>

              {/* Match Scoring & Candidate Info */}
              <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 0.8fr', gap: '12px' }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  <div style={{ background: 'var(--surface-fog)', padding: '12px', borderRadius: '12px', border: '1px solid var(--border)' }}>
                    <div style={{ fontSize: '10px', color: 'var(--color-graphite)', textTransform: 'uppercase' }}>Verified Applicant</div>
                    <div style={{ fontSize: '14px', fontWeight: 500, color: 'var(--text)', marginTop: '2px' }}>Sarah K.</div>
                    <div style={{ fontSize: '11px', color: 'var(--color-rust)', marginTop: '4px', fontWeight: 550 }}>✓ 94% Suitability Score</div>
                  </div>
                  <div style={{ display: 'flex', gap: '8px' }}>
                    <div style={{ flex: 1, background: 'var(--surface-fog)', padding: '8px', borderRadius: '8px', textAlign: 'center', border: '1px solid var(--border)' }}>
                      <div style={{ fontSize: '13px', fontWeight: 600 }}>98%</div>
                      <div style={{ fontSize: '8px', color: 'var(--color-graphite)' }}>Authenticity</div>
                    </div>
                    <div style={{ flex: 1, background: 'var(--surface-fog)', padding: '8px', borderRadius: '8px', textAlign: 'center', border: '1px solid var(--border)' }}>
                      <div style={{ fontSize: '13px', fontWeight: 600 }}>12%</div>
                      <div style={{ fontSize: '8px', color: 'var(--color-rust)' }}>Risk Score</div>
                    </div>
                  </div>
                </div>

                {/* Score Dial / Ring */}
                <div style={{ background: 'var(--surface-fog)', borderRadius: '12px', padding: '12px', display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', border: '1px solid var(--border)' }}>
                  <div style={{ width: '48px', height: '48px', borderRadius: '50%', border: '3px solid var(--color-rust)', display: 'grid', placeItems: 'center', fontSize: '13px', fontWeight: 600 }}>
                    94%
                  </div>
                  <span style={{ fontSize: '9px', color: 'var(--color-graphite)', marginTop: '6px' }}>AI Recommendation</span>
                </div>
              </div>

              {/* Pipeline Kanban Columns */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '10px' }}>
                {['Screening', 'Interviews', 'Offer'].map((col, idx) => (
                  <div key={idx} style={{ background: 'var(--surface-fog)', padding: '10px', borderRadius: '8px', border: '1px solid var(--border)' }}>
                    <div style={{ fontSize: '9px', fontWeight: 600, color: 'var(--color-graphite)', textTransform: 'uppercase', marginBottom: '6px', display: 'flex', justifyContent: 'space-between' }}>
                      <span>{col}</span>
                      <span>{idx === 0 ? '2' : '1'}</span>
                    </div>
                    <div style={{ background: 'var(--surface-card)', padding: '8px', borderRadius: '6px', border: '1px solid var(--border)', fontSize: '10px', fontWeight: 500 }}>
                      {idx === 0 ? 'Alex M.' : idx === 1 ? 'Sarah K.' : 'Elena R.'}
                    </div>
                  </div>
                ))}
              </div>
            </motion.div>

            <div>
              <span style={{ fontSize: 10, color: 'var(--color-rust)', letterSpacing: '0.12em', textTransform: 'uppercase', fontWeight: 600 }}>Hiring Control Room</span>
              <h2 style={{ fontSize: 'var(--text-heading)', fontWeight: 400, color: 'var(--text)', marginTop: 'var(--space-2)', fontFamily: 'var(--font-signifier)', lineHeight: 1.1, letterSpacing: '-0.020em' }}>
                Recruiter Command Center
              </h2>
              <p style={{ fontSize: 'var(--text-body)', color: 'var(--color-ash)', marginTop: 'var(--space-6)', lineHeight: 1.45 }}>
                Coordinate applicant reviews, schedule panels, and evaluate candidates in one consolidated admin command cockpit. Get verified signals rather than parsing candidate stacks manually.
              </p>
              <ul style={{ paddingLeft: '18px', marginTop: 'var(--space-6)', display: 'flex', flexDirection: 'column', gap: '10px', fontSize: 'var(--text-caption)', color: 'var(--color-ash)' }}>
                <li>🤖 <strong>AI Screening Queue:</strong> Automated candidate sorting maps profile telemetry instantly.</li>
                <li>📋 <strong>Hiring Pipeline:</strong> Dynamic Kanban columns manage candidates from application to contract sign.</li>
                <li>🗓️ <strong>Interview Coordinator:</strong> zentralized panels with Google Meet links keep loops moving.</li>
                <li>✓ <strong>Authenticity Metrics:</strong> Risk and evidence profiles ensure recruiter confidence.</li>
              </ul>
            </div>
          </div>
        </div>
      </section>

      {/* Trust Layer Section */}
      <section id="trust-layer" style={{
        background: 'var(--surface-fog)',
        borderTop: '1px solid var(--border)',
        borderBottom: '1px solid var(--border)',
        padding: 'var(--spacing-96) 0',
        position: 'relative',
        zIndex: 1
      }}>
        <div style={{ maxWidth: 1200, margin: '0 auto', padding: '0 var(--space-6)' }}>
          <div style={{ textAlign: 'center', marginBottom: 'var(--space-16)' }}>
            <span style={{ fontSize: 10, color: 'var(--color-rust)', letterSpacing: '0.12em', textTransform: 'uppercase', fontWeight: 600 }}>Enterprise-Grade Boundaries</span>
            <h2 style={{ fontSize: 'var(--text-heading-sm)', fontWeight: 500, color: 'var(--text)', marginTop: 'var(--space-2)', fontFamily: 'var(--font-signifier)', letterSpacing: '-0.02em' }}>
              The SmartOnboard Trust Layer
            </h2>
            <p style={{ fontSize: 'var(--text-body)', color: 'var(--color-ash)', marginTop: 'var(--space-3)', maxWidth: 540, marginInline: 'auto' }}>
              Strict verification barriers and role-based data isolation keep hiring secure.
            </p>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '24px' }}>
            {[
              { title: 'Domain DNS Verification', desc: 'Recruiters are validated using strict DNS MX checks to block unauthorized workspaces.', icon: '🌐' },
              { title: 'Role Metadata Isolation', desc: 'Recruiter-specific risk, evidence scores, and interview reviews are strictly hidden from candidates.', icon: '🔒' },
              { title: 'Identity OTP Gates', desc: 'Every account is confirmed using Twilio phone OTP and email challenge loops.', icon: '🛡️' },
              { title: 'Hiring Action Audit Logs', desc: 'Pipeline shifts, panel scores, and hiring actions are logged for compliance reviews.', icon: '📝' }
            ].map((item, idx) => (
              <motion.div
                key={idx}
                initial={{ opacity: 0, y: 15 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.35, delay: idx * 0.05 }}
                className="card"
                style={{
                  padding: '24px',
                  background: 'var(--surface-card)',
                  borderRadius: '20px',
                  border: '1px solid var(--border)',
                  boxShadow: 'var(--shadow-subtle)'
                }}
              >
                <div style={{ fontSize: '24px', marginBottom: '12px' }}>{item.icon}</div>
                <h3 style={{ fontSize: '15px', fontWeight: 600, color: 'var(--text)', marginBottom: '8px' }}>{item.title}</h3>
                <p style={{ fontSize: 'var(--text-caption)', color: 'var(--color-graphite)', margin: 0, lineHeight: 1.4 }}>{item.desc}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing Section */}
      <motion.section
        id="pricing"
        initial={{ opacity: 0, y: 15 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, margin: '-100px' }}
        transition={{ duration: 0.4, ease: 'easeOut' }}
        style={{
          borderTop: '1px dashed var(--color-cork-shadow)',
          padding: 'var(--spacing-96) var(--space-6)',
          position: 'relative',
          zIndex: 1
        }}
      >
        <div style={{ maxWidth: 1000, margin: '0 auto' }}>
          <div style={{ textAlign: 'center', marginBottom: 'var(--space-12)' }}>
            <span style={{ fontSize: 10, color: 'var(--color-ash)', letterSpacing: '0.05em', textTransform: 'uppercase' }}>
              Simple Pricing
            </span>
            <h2 style={{ fontSize: 'var(--text-heading-sm)', fontWeight: 500, color: 'var(--text)', marginTop: 'var(--space-2)' }}>
              Transparent Plans. No Hidden Costs.
            </h2>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 'var(--space-6)' }}>
            {/* Candidate Plan */}
            <motion.div
              whileHover={{ y: -3, scale: 1.015, borderColor: 'var(--color-rust)' }}
              transition={{ duration: 0.25, ease: 'easeOut' }}
              style={{ border: '1px solid var(--color-cork-shadow)', borderRadius: 'var(--radius-cards)', padding: 'var(--space-8)', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', minHeight: 320, background: 'var(--surface-card)', cursor: 'default', boxShadow: 'var(--shadow-subtle)' }}
            >
              <div>
                <h3 style={{ fontSize: 'var(--text-subheading)', fontWeight: 500, color: 'var(--text)' }}>
                  Job Seekers
                </h3>
                <div style={{ display: 'flex', alignItems: 'baseline', margin: 'var(--space-4) 0' }}>
                  <span style={{ fontSize: 'var(--text-heading)', fontWeight: 500, color: 'var(--text)' }}>Free</span>
                  <span style={{ fontSize: 'var(--text-caption)', color: 'var(--color-ash)', marginLeft: 'var(--space-2)' }}>forever</span>
                </div>
                <p style={{ fontSize: 'var(--text-caption)', color: 'var(--color-ash)', lineHeight: 'var(--leading-normal)' }}>
                  Build a verified identity, upload up to 3 resumes, and view match alignment scoring across all active roles.
                </p>
              </div>
              <Link to="/register" className="btn btn--secondary btn--block" style={{ marginTop: 'var(--space-6)', borderRadius: 'var(--radius-buttons)' }}>
                Create Free Profile
              </Link>
            </motion.div>

            {/* Recruiter Plan */}
            <motion.div
              whileHover={{ y: -3, scale: 1.015, borderColor: 'var(--color-rust)' }}
              transition={{ duration: 0.25, ease: 'easeOut' }}
              style={{ border: '1px solid var(--color-rust)', borderRadius: 'var(--radius-cards)', padding: 'var(--space-8)', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', minHeight: 320, background: 'var(--surface-card)', cursor: 'default', boxShadow: 'var(--shadow-subtle)' }}
            >
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <h3 style={{ fontSize: 'var(--text-subheading)', fontWeight: 500, color: 'var(--text)' }}>
                    Recruiter Workspace
                  </h3>
                  <span className="badge badge--hire" style={{ borderColor: 'var(--color-rust)', color: 'var(--color-rust)' }}>Active</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'baseline', margin: 'var(--space-4) 0' }}>
                  <span style={{ fontSize: 'var(--text-heading)', fontWeight: 500, color: 'var(--text)' }}>$49</span>
                  <span style={{ fontSize: 'var(--text-caption)', color: 'var(--color-ash)', marginLeft: 'var(--space-2)' }}>/ month per active job</span>
                </div>
                <p style={{ fontSize: 'var(--text-caption)', color: 'var(--color-ash)', lineHeight: 'var(--leading-normal)' }}>
                  Post jobs, access unlimited matching candidates, review risk/authenticity evidence metrics, and manage custom pipeline stages.
                </p>
              </div>
              <Link to="/register" className="btn btn--primary btn--block" style={{ marginTop: 'var(--space-6)', background: 'var(--color-ink)', color: 'var(--color-pure-white)', borderRadius: 'var(--radius-buttons)' }}>
                Get Started
              </Link>
            </motion.div>
          </div>
        </div>
      </motion.section>

      {/* Trust & Factual Metrics */}
      <section style={{
        padding: 'var(--spacing-64) var(--space-6)',
        borderBottom: '1px solid var(--color-cork-shadow)',
        borderTop: '1px solid var(--color-cork-shadow)',
        background: 'var(--surface-fog)',
        position: 'relative',
        zIndex: 1
      }}>
        <div style={{
          maxWidth: 1200,
          margin: '0 auto',
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
          gap: 'var(--space-6)',
          textAlign: 'center'
        }}>
          <div>
            <div style={{ fontSize: 'var(--text-heading)', fontWeight: 500, color: 'var(--color-rust)' }}>
              $<AnimatedCounter value={49} />
            </div>
            <div style={{ fontSize: '11px', color: 'var(--color-graphite)', textTransform: 'uppercase', marginTop: 'var(--space-2)', fontWeight: 600, letterSpacing: '0.05em' }}>
              Per Month Per Active Job
            </div>
          </div>
          <div>
            <div style={{ fontSize: 'var(--text-heading)', fontWeight: 500, color: 'var(--text)' }}>
              <AnimatedCounter value={3} />
            </div>
            <div style={{ fontSize: '11px', color: 'var(--color-graphite)', textTransform: 'uppercase', marginTop: 'var(--space-2)', fontWeight: 600, letterSpacing: '0.05em' }}>
              Resumes Max Per Candidate
            </div>
          </div>
          <div>
            <div style={{ fontSize: 'var(--text-heading)', fontWeight: 500, color: 'var(--text)' }}>
              <AnimatedCounter value={100} />%
            </div>
            <div style={{ fontSize: '11px', color: 'var(--color-graphite)', textTransform: 'uppercase', marginTop: 'var(--space-2)', fontWeight: 600, letterSpacing: '0.05em' }}>
              Mandatory OTP Verification
            </div>
          </div>
          <div>
            <div style={{ fontSize: 'var(--text-heading)', fontWeight: 500, color: 'var(--text)' }}>
              <AnimatedCounter value={activeJobsCount} />
            </div>
            <div style={{ fontSize: '11px', color: 'var(--color-graphite)', textTransform: 'uppercase', marginTop: 'var(--space-2)', fontWeight: 600, letterSpacing: '0.05em' }}>
              Active Job Openings
            </div>
          </div>
        </div>
      </section>

      {/* About Section */}
      <motion.section
        id="about"
        initial={{ opacity: 0, y: 15 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, margin: '-100px' }}
        transition={{ duration: 0.4, ease: 'easeOut' }}
        style={{
          padding: 'var(--spacing-96) var(--space-6)',
          position: 'relative',
          zIndex: 1
        }}
      >
        <div style={{ maxWidth: 800, margin: '0 auto', textAlign: 'center' }}>
          <span style={{ fontSize: 10, color: 'var(--color-rust)', letterSpacing: '0.05em', textTransform: 'uppercase' }}>
            Our Philosophy
          </span>
          <h2 style={{ fontSize: 'var(--text-heading-sm)', fontWeight: 500, color: 'var(--text)', marginTop: 'var(--space-2)', marginBottom: 'var(--space-4)' }}>
            Trust Over Volume
          </h2>
          <p style={{ fontSize: 'var(--text-body)', color: 'var(--color-ash)', lineHeight: 'var(--leading-normal)', marginInline: 'auto', maxWidth: 640 }}>
            SmartOnboard is built to combat the friction of application spam. We don't optimize for vanity volume. We optimize for credential verification, objective skills verification, and robust signals so that recruiters can discover matches they can trust.
          </p>
        </div>
      </motion.section>

      {/* Footer */}
      <footer style={{
        borderTop: '1px solid var(--color-cork-shadow)',
        padding: 'var(--space-10) var(--space-6)',
        textAlign: 'center',
        position: 'relative',
        zIndex: 1
      }}>
        <div style={{
          maxWidth: 1200,
          margin: '0 auto',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: 'var(--space-4)'
        }}>
          <div style={{ fontSize: 12, fontWeight: 600, letterSpacing: '0.05em' }}>
            SMARTONBOARD
          </div>
          <div style={{ fontSize: 11, color: 'var(--color-graphite)', display: 'flex', gap: 'var(--space-3)', justifyContent: 'center' }}>
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
          <p style={{ fontSize: 11, color: 'var(--color-dove)', marginTop: 'var(--space-2)' }}>
            &copy; 2026 SmartOnboard. All rights reserved. Built with verification integrity.
          </p>
        </div>
      </footer>
    </div>
  )
}
