import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { fetchJobs } from '../api'
import AnimatedCounter from '../components/AnimatedCounter'

import SteepCard from '../components/design-system/SteepCard'
import SteepButton from '../components/design-system/SteepButton'
import SteepBadge from '../components/design-system/SteepBadge'

export default function Landing() {
  const [activeJobsCount, setActiveJobsCount] = useState(0)

  useEffect(() => {
    fetchJobs('open')
      .then((data) => setActiveJobsCount(data.length))
      .catch(() => setActiveJobsCount(0))
  }, [])

  const handleScrollTo = (e: React.MouseEvent<HTMLAnchorElement | HTMLButtonElement>, id: string) => {
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
      background: 'var(--color-fog)',
      color: 'var(--color-ink)',
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
            background: 'var(--surface-cool-tint)',
            filter: 'blur(130px)',
            opacity: 0.35,
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
            background: 'var(--surface-warm-tint)',
            filter: 'blur(150px)',
            opacity: 0.3,
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
        background: 'var(--color-pure-white)',
        borderBottom: '1px solid var(--border)',
        backdropFilter: 'blur(12px)'
      }}>
        <div style={{
          maxWidth: 1200,
          margin: '0 auto',
          padding: '0 var(--spacing-24)',
          height: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 'var(--spacing-16)',
          position: 'relative',
          zIndex: 1
        }}>
          {/* Logo */}
          <Link to="/" style={{ display: 'flex', alignItems: 'center', gap: 'var(--spacing-12)', fontWeight: 500, fontSize: '18px', letterSpacing: '-0.02em', color: 'var(--color-ink)', textDecoration: 'none' }}>
            <span style={{ width: '24px', height: '24px', borderRadius: '50%', background: 'var(--color-ink)', display: 'inline-block' }} />
            SmartOnboard
          </Link>

          {/* Nav Links */}
          <nav style={{ display: 'flex', alignItems: 'center', gap: 'var(--spacing-8)' }}>
            <a href="#features" onClick={(e) => handleScrollTo(e, 'features')} className="nav-link" style={{ fontSize: '15px', color: 'var(--color-ink)' }}>
              Features
            </a>
            <a href="#solutions" onClick={(e) => handleScrollTo(e, 'solutions')} className="nav-link" style={{ fontSize: '15px', color: 'var(--color-ink)' }}>
              Solutions
            </a>
            <a href="#pricing" onClick={(e) => handleScrollTo(e, 'pricing')} className="nav-link" style={{ fontSize: '15px', color: 'var(--color-ink)' }}>
              Pricing
            </a>
            <a href="#about" onClick={(e) => handleScrollTo(e, 'about')} className="nav-link" style={{ fontSize: '15px', color: 'var(--color-ink)' }}>
              About
            </a>
          </nav>

          {/* Auth Actions */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--spacing-12)' }}>
            <SteepButton variant="ghost" size="sm" to="/login">
              Login
            </SteepButton>
            <SteepButton variant="primary" size="sm" to="/register">
              Register
            </SteepButton>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <motion.section
        initial={{ opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
        style={{
          minHeight: 'calc(70vh - var(--header-h))',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          alignItems: 'center',
          textAlign: 'center',
          padding: 'var(--spacing-64) var(--spacing-24)',
          maxWidth: 900,
          margin: '0 auto',
          position: 'relative',
          zIndex: 1,
          background: 'radial-gradient(circle, rgba(251, 225, 209, 0.35) 0%, rgba(255, 255, 255, 0) 70%)'
        }}
      >
        {/* Orbiting Card 1: Stat Card with Delta */}
        <div className="hero-floating-card" style={{ top: '12%', left: '-18%', width: '190px', zIndex: 2, position: 'absolute' }}>
          <SteepCard variant="default" padding="compact">
            <span style={{ fontSize: '11px', color: 'var(--color-ash)', textTransform: 'uppercase', fontWeight: 600, letterSpacing: '0.05em' }}>Verification Rate</span>
            <div style={{ fontSize: '30px', fontWeight: 500, margin: '8px 0 4px', color: 'var(--color-ink)', letterSpacing: '-0.02em' }}>98.4%</div>
            <span style={{ fontSize: '12px', color: 'var(--success)', fontWeight: 500 }}>↑ +3.2% this week</span>
          </SteepCard>
        </div>

        {/* Orbiting Card 2: Donut Chart with a Rust stroke on Apricot Wash background (Warm Apricot Wash) */}
        <div className="hero-floating-card" style={{ top: '8%', right: '-20%', width: '220px', zIndex: 2, position: 'absolute' }}>
          <SteepCard variant="warm" padding="compact" style={{ borderColor: 'var(--color-rust)' }}>
            <span style={{ fontSize: '11px', color: 'var(--color-rust)', textTransform: 'uppercase', fontWeight: 600, letterSpacing: '0.05em' }}>Fit Distribution</span>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginTop: '4px' }}>
              <svg width="56" height="56" viewBox="0 0 36 36" style={{ transform: 'rotate(-90deg)' }}>
                <circle cx="18" cy="18" r="15.915" fill="none" stroke="rgba(93, 42, 26, 0.12)" strokeWidth="3.5" />
                <circle cx="18" cy="18" r="15.915" fill="none" stroke="var(--color-rust)" strokeWidth="3.5" strokeDasharray="78 22" strokeDashoffset="0" />
              </svg>
              <div>
                <div style={{ fontSize: '17px', fontWeight: 500, color: 'var(--color-rust)', letterSpacing: '-0.01em' }}>78% Fit</div>
                <div style={{ fontSize: '11px', color: 'var(--color-rust)', opacity: 0.8 }}>Verified Match</div>
              </div>
            </div>
          </SteepCard>
        </div>

        {/* Orbiting Card 3: AI Response Bubble with Avatar Badge */}
        <div className="hero-floating-card" style={{ bottom: '1%', left: '-22%', width: '280px', zIndex: 2, position: 'absolute' }}>
          <SteepCard variant="default" padding="compact">
            <div style={{ position: 'absolute', top: '-16px', left: '-16px', width: '34px', height: '34px', borderRadius: '50%', background: 'var(--surface-warm-tint)', border: '2px solid var(--color-pure-white)', display: 'grid', placeItems: 'center', fontSize: '12px', fontWeight: 600, color: 'var(--color-ink)', boxShadow: 'var(--shadow-subtle)' }}>
              AI
            </div>
            <div style={{ background: 'var(--surface-cool-tint)', borderRadius: '16px', padding: '12px', marginBottom: '12px' }}>
              <div style={{ fontSize: '11px', color: 'var(--color-ink)', fontWeight: 600, marginBottom: '4px' }}>Skills Match Curve</div>
              <svg width="100%" height="32" viewBox="0 0 100 40" preserveAspectRatio="none">
                <path d="M0,35 Q25,18 50,26 T100,8" fill="none" stroke="var(--color-ink)" strokeWidth="2.5" />
                <path d="M0,38 Q25,23 50,31 T100,16" fill="none" stroke="var(--color-rust)" strokeWidth="2.5" strokeDasharray="3 3" />
              </svg>
            </div>
            <h4 style={{ fontSize: '14px', fontWeight: 500, color: 'var(--color-ink)', margin: '0 0 4px' }}>Optimal Candidate Found</h4>
            <p style={{ fontSize: '12px', color: 'var(--color-ash)', margin: 0, lineHeight: 1.35 }}>Sarah K. has verified React/TypeScript credentials matching your architect post.</p>
          </SteepCard>
        </div>

        {/* Orbiting Card 4: Chat Input Field */}
        <div className="hero-floating-card" style={{ bottom: '4%', right: '-18%', width: '260px', zIndex: 2, position: 'absolute' }}>
          <SteepCard variant="default" padding="compact" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderRadius: '20px' }}>
            <span style={{ fontSize: '12.5px', color: 'var(--color-ash)' }}>Search verified architects...</span>
            <div style={{ width: '30px', height: '30px', borderRadius: '50%', background: 'var(--color-ink)', display: 'grid', placeItems: 'center', color: 'var(--color-pure-white)', fontSize: '12px', cursor: 'pointer' }}>
              →
            </div>
          </SteepCard>
        </div>

        <motion.span 
          initial={{ opacity: 0, y: 5 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1, duration: 0.3 }}
          style={{
            fontSize: 11,
            fontWeight: 500,
            color: 'var(--color-rust)',
            letterSpacing: '0.12em',
            textTransform: 'uppercase',
            marginBottom: 'var(--spacing-16)'
          }}
        >
          Verified Hiring Ecosystem
        </motion.span>
        
        <h1 style={{
          fontFamily: 'var(--font-signifier)',
          fontSize: 'var(--text-heading-lg)',
          fontWeight: 400,
          lineHeight: 1.05,
          letterSpacing: '-1.6px',
          color: 'var(--color-ink)',
          margin: 'var(--spacing-8) 0 var(--spacing-16)',
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
            lineHeight: 1.35,
            color: 'var(--color-ash)',
            maxWidth: 600,
            margin: '0 0 var(--spacing-32)'
          }}
        >
          Built to maximize recruiter trust and candidate fit. Screen resumes, verify candidates with OTP, and make confident placement decisions.
        </motion.p>

        {/* Hero CTAs */}
        <motion.div 
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5, duration: 0.3 }}
          style={{ display: 'flex', gap: 'var(--spacing-20)', alignItems: 'center', justifyContent: 'center' }}
        >
          <motion.div whileHover={{ scale: 1.015 }} whileTap={{ scale: 0.985 }}>
            <SteepButton variant="primary" size="lg" to="/register">
              Get Started
            </SteepButton>
          </motion.div>
          <motion.div whileHover={{ scale: 1.015 }} whileTap={{ scale: 0.985 }}>
            <SteepButton variant="ghost" size="lg" href="#features" onClick={(e) => handleScrollTo(e, 'features')}>
              Learn More &rarr;
            </SteepButton>
          </motion.div>
        </motion.div>
      </motion.section>

      {/* Workflow Story Section */}
      <section style={{
        maxWidth: 1200,
        margin: '0 auto var(--spacing-64)',
        padding: '0 var(--spacing-24)',
        position: 'relative',
        zIndex: 1
      }}>
        <div style={{ textAlign: 'center', marginBottom: 'var(--spacing-32)' }}>
          <span style={{ fontSize: 10, color: 'var(--color-rust)', letterSpacing: '0.12em', textTransform: 'uppercase', fontWeight: 600 }}>The SmartOnboard Loop</span>
          <h2 className="font-signifier" style={{ fontSize: 'var(--text-heading-sm)', fontWeight: 500, color: 'var(--color-ink)', marginTop: 'var(--spacing-8)' }}>
            Unified Sourcing & Verification Sequence
          </h2>
        </div>

        {/* Visual Workflow Steps */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '16px', position: 'relative' }}>
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
              style={{ display: 'flex', flexDirection: 'column', height: '100%' }}
            >
              <SteepCard style={{ textAlign: 'center', height: '100%', display: 'flex', flexDirection: 'column', gap: 'var(--spacing-8)' }}>
                <div style={{ fontSize: '10px', fontWeight: 600, color: 'var(--color-rust)' }}>{item.step}</div>
                <div style={{ fontSize: '24px' }}>{item.icon}</div>
                <h4 style={{ fontSize: '14px', fontWeight: 500, color: 'var(--color-ink)', margin: 0, lineHeight: 1.2 }}>{item.title}</h4>
                <p style={{ fontSize: '11px', color: 'var(--color-ash)', margin: 0, lineHeight: 1.3 }}>{item.desc}</p>
              </SteepCard>
            </motion.div>
          ))}
        </div>
      </section>

      {/* Candidate Verification Engine */}
      <section id="verification-engine" style={{
        background: 'var(--color-pure-white)',
        borderTop: '1px solid var(--border)',
        borderBottom: '1px solid var(--border)',
        padding: 'var(--spacing-80) 0',
        position: 'relative',
        zIndex: 1
      }}>
        <div style={{ maxWidth: 1200, margin: '0 auto', padding: '0 var(--spacing-24)' }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1.2fr', gap: 'var(--spacing-40)', alignItems: 'center' }}>
            <div>
              <span style={{ fontSize: 10, color: 'var(--color-rust)', letterSpacing: '0.12em', textTransform: 'uppercase', fontWeight: 600 }}>Zero Application Spam</span>
              <h2 className="font-signifier" style={{ fontSize: 'var(--text-heading-sm)', fontWeight: 500, color: 'var(--color-ink)', marginTop: 'var(--spacing-8)' }}>
                Candidate Verification Engine
              </h2>
              <p style={{ fontSize: 'var(--text-body)', color: 'var(--color-ash)', marginTop: 'var(--spacing-16)', lineHeight: 1.45 }}>
                Ensure applicant legitimacy at the front door. We replace vanity applicant volume with concrete trust signals, forcing verification before recruiters review portfolios.
              </p>
              <ul style={{ paddingLeft: '18px', marginTop: 'var(--spacing-16)', display: 'flex', flexDirection: 'column', gap: '10px', fontSize: 'var(--text-caption)', color: 'var(--color-ash)' }}>
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
            >
              <SteepCard style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border)', paddingBottom: '12px' }}>
                  <span style={{ fontSize: '11px', fontWeight: 600, color: 'var(--color-rust)', letterSpacing: '0.08em', textTransform: 'uppercase' }}>Candidate Workspace Preview</span>
                  <SteepBadge variant="success">Profile: 100% Verified</SteepBadge>
                </div>

                {/* Upload block */}
                <div style={{ padding: '14px', borderRadius: 'var(--radius-inputs)', border: '1px dashed var(--border)', background: 'var(--color-fog)', textAlign: 'center' }}>
                  <div style={{ fontSize: '18px', marginBottom: '4px' }}>📄</div>
                  <div style={{ fontSize: '12px', fontWeight: 500, color: 'var(--color-ink)' }}>active_resume_frontend.pdf</div>
                  <div style={{ fontSize: '10px', color: 'var(--color-ash)', marginTop: '2px' }}>Resume 1 of 3 uploaded &bull; Verified 94% Skills Fit</div>
                </div>

                {/* Extracted skills block */}
                <div>
                  <div style={{ fontSize: '10px', fontWeight: 600, textTransform: 'uppercase', color: 'var(--color-ash)', marginBottom: '8px' }}>Extracted Skill Matrix</div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                    {['React', 'TypeScript', 'Node.js', 'PostgreSQL', 'Git'].map(s => (
                      <SteepBadge key={s} variant="success">✓ {s}</SteepBadge>
                    ))}
                    <SteepBadge variant="danger">✕ Kubernetes</SteepBadge>
                  </div>
                </div>

                {/* Verification checks block */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {[
                    { label: 'Email Verification OTP Gate', status: 'VERIFIED', active: true },
                    { label: 'Twilio Phone SMS OTP Gateway', status: 'VERIFIED', active: true },
                    { label: 'Organizational Fit Scorer', status: '94% COMPATIBLE', active: false }
                  ].map((item, idx) => (
                    <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'var(--color-fog)', padding: '10px 14px', borderRadius: 'var(--radius-inputs)', fontSize: '11.5px' }}>
                      <span style={{ color: 'var(--color-ash)' }}>{item.label}</span>
                      <span style={{ fontSize: '9.5px', fontWeight: 600, color: item.active ? 'var(--success)' : 'var(--color-rust)' }}>{item.status}</span>
                    </div>
                  ))}
                </div>
              </SteepCard>
            </motion.div>
          </div>
        </div>
      </section>

      {/* Recruiter Command Center */}
      <section id="command-center" style={{
        padding: 'var(--spacing-80) 0',
        position: 'relative',
        zIndex: 1
      }}>
        <div style={{ maxWidth: 1200, margin: '0 auto', padding: '0 var(--spacing-24)' }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: 'var(--spacing-40)', alignItems: 'center' }}>
            {/* Interactive Recruiter Dashboard Preview */}
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
            >
              <SteepCard style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border)', paddingBottom: '12px' }}>
                  <div>
                    <span style={{ fontSize: '11px', fontWeight: 600, color: 'var(--color-rust)', letterSpacing: '0.08em', textTransform: 'uppercase' }}>Hiring Control Cockpit</span>
                    <div style={{ fontSize: '12px', color: 'var(--color-ash)', marginTop: '2px' }}>Active Job: Lead React Architect</div>
                  </div>
                  <SteepBadge variant="interview">AI Queue: Active</SteepBadge>
                </div>

                {/* Match Scoring & Candidate Info */}
                <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 0.8fr', gap: '12px' }}>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                    <div style={{ background: 'var(--color-fog)', padding: '12px', borderRadius: 'var(--radius-inputs)', border: '1px solid var(--border)' }}>
                      <div style={{ fontSize: '10px', color: 'var(--color-ash)', textTransform: 'uppercase' }}>Verified Applicant</div>
                      <div style={{ fontSize: '14px', fontWeight: 500, color: 'var(--color-ink)', marginTop: '2px' }}>Sarah K.</div>
                      <div style={{ fontSize: '11px', color: 'var(--color-rust)', marginTop: '4px', fontWeight: 600 }}>✓ 94% Suitability Score</div>
                    </div>
                    <div style={{ display: 'flex', gap: '8px' }}>
                      <div style={{ flex: 1, background: 'var(--color-fog)', padding: '8px', borderRadius: 'var(--radius-inputs)', textAlign: 'center', border: '1px solid var(--border)' }}>
                        <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--color-ink)' }}>98%</div>
                        <div style={{ fontSize: '8px', color: 'var(--color-ash)' }}>Authenticity</div>
                      </div>
                      <div style={{ flex: 1, background: 'var(--color-fog)', padding: '8px', borderRadius: 'var(--radius-inputs)', textAlign: 'center', border: '1px solid var(--border)' }}>
                        <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--color-rust)' }}>12%</div>
                        <div style={{ fontSize: '8px', color: 'var(--color-rust)' }}>Risk Score</div>
                      </div>
                    </div>
                  </div>

                  {/* Score Dial / Ring */}
                  <div style={{ background: 'var(--color-fog)', borderRadius: 'var(--radius-inputs)', padding: '12px', display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', border: '1px solid var(--border)' }}>
                    <div style={{ width: '48px', height: '48px', borderRadius: '50%', border: '3px solid var(--color-rust)', display: 'grid', placeItems: 'center', fontSize: '13px', fontWeight: 600, color: 'var(--color-rust)' }}>
                      94%
                    </div>
                    <span style={{ fontSize: '9px', color: 'var(--color-ash)', marginTop: '6px' }}>AI Recommendation</span>
                  </div>
                </div>

                {/* Pipeline Kanban Columns */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '10px' }}>
                  {['Screening', 'Interviews', 'Offer'].map((col, idx) => (
                    <div key={idx} style={{ background: 'var(--color-fog)', padding: '10px', borderRadius: 'var(--radius-inputs)', border: '1px solid var(--border)' }}>
                      <div style={{ fontSize: '9px', fontWeight: 600, color: 'var(--color-ash)', textTransform: 'uppercase', marginBottom: '6px', display: 'flex', justifyContent: 'space-between' }}>
                        <span>{col}</span>
                        <span style={{ color: 'var(--color-ink)' }}>{idx === 0 ? '2' : '1'}</span>
                      </div>
                      <div style={{ background: 'var(--color-pure-white)', padding: '8px', borderRadius: 'var(--radius-inputs)', border: '1px solid var(--border)', fontSize: '10px', fontWeight: 500, color: 'var(--color-ink)' }}>
                        {idx === 0 ? 'Alex M.' : idx === 1 ? 'Sarah K.' : 'Elena R.'}
                      </div>
                    </div>
                  ))}
                </div>
              </SteepCard>
            </motion.div>

            <div>
              <span style={{ fontSize: 10, color: 'var(--color-rust)', letterSpacing: '0.12em', textTransform: 'uppercase', fontWeight: 600 }}>Hiring Control Room</span>
              <h2 className="font-signifier" style={{ fontSize: 'var(--text-heading-sm)', fontWeight: 500, color: 'var(--color-ink)', marginTop: 'var(--spacing-8)' }}>
                Recruiter Command Center
              </h2>
              <p style={{ fontSize: 'var(--text-body)', color: 'var(--color-ash)', marginTop: 'var(--spacing-16)', lineHeight: 1.45 }}>
                Coordinate applicant reviews, schedule panels, and evaluate candidates in one consolidated admin command cockpit. Get verified signals rather than parsing candidate stacks manually.
              </p>
              <ul style={{ paddingLeft: '18px', marginTop: 'var(--spacing-16)', display: 'flex', flexDirection: 'column', gap: '10px', fontSize: 'var(--text-caption)', color: 'var(--color-ash)' }}>
                <li>🤖 <strong>AI Screening Queue:</strong> Automated candidate sorting maps profile telemetry instantly.</li>
                <li>📋 <strong>Hiring Pipeline:</strong> Dynamic Kanban columns manage candidates from application to contract sign.</li>
                <li>🗓️ <strong>Interview Coordinator:</strong> Centralized panels with Google Meet links keep loops moving.</li>
                <li>✓ <strong>Authenticity Metrics:</strong> Risk and evidence profiles ensure recruiter confidence.</li>
              </ul>
            </div>
          </div>
        </div>
      </section>

      {/* Trust Layer Section */}
      <section id="trust-layer" style={{
        background: 'var(--color-pure-white)',
        borderTop: '1px solid var(--border)',
        borderBottom: '1px solid var(--border)',
        padding: 'var(--spacing-80) 0',
        position: 'relative',
        zIndex: 1
      }}>
        <div style={{ maxWidth: 1200, margin: '0 auto', padding: '0 var(--spacing-24)' }}>
          <div style={{ textAlign: 'center', marginBottom: 'var(--spacing-32)' }}>
            <span style={{ fontSize: 10, color: 'var(--color-rust)', letterSpacing: '0.12em', textTransform: 'uppercase', fontWeight: 600 }}>Enterprise-Grade Boundaries</span>
            <h2 className="font-signifier" style={{ fontSize: 'var(--text-heading-sm)', fontWeight: 500, color: 'var(--color-ink)', marginTop: 'var(--spacing-8)' }}>
              The SmartOnboard Trust Layer
            </h2>
            <p style={{ fontSize: 'var(--text-body)', color: 'var(--color-ash)', marginTop: 'var(--spacing-8)', maxWidth: 540, marginInline: 'auto' }}>
              Strict verification barriers and role-based data isolation keep hiring secure.
            </p>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '24px' }}>
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
                style={{ display: 'flex', flexDirection: 'column', height: '100%' }}
              >
                <SteepCard style={{ height: '100%', display: 'flex', flexDirection: 'column', gap: 'var(--spacing-8)' }}>
                  <div style={{ fontSize: '24px' }}>{item.icon}</div>
                  <h3 style={{ fontSize: '15px', fontWeight: 600, color: 'var(--color-ink)', margin: 0 }}>{item.title}</h3>
                  <p style={{ fontSize: 'var(--text-caption)', color: 'var(--color-ash)', margin: 0, lineHeight: 1.4 }}>{item.desc}</p>
                </SteepCard>
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
          padding: 'var(--spacing-80) var(--spacing-24)',
          position: 'relative',
          zIndex: 1
        }}
      >
        <div style={{ maxWidth: 1000, margin: '0 auto' }}>
          <div style={{ textAlign: 'center', marginBottom: 'var(--spacing-32)' }}>
            <span style={{ fontSize: 10, color: 'var(--color-ash)', letterSpacing: '0.05em', textTransform: 'uppercase' }}>
              Simple Pricing
            </span>
            <h2 className="font-signifier" style={{ fontSize: 'var(--text-heading-sm)', fontWeight: 500, color: 'var(--color-ink)', marginTop: 'var(--spacing-8)' }}>
              Transparent Plans. No Hidden Costs.
            </h2>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '24px' }}>
            {/* Candidate Plan */}
            <motion.div
              whileHover={{ y: -3, scale: 1.015 }}
              transition={{ duration: 0.25, ease: 'easeOut' }}
              style={{ display: 'flex', flexDirection: 'column', height: '100%' }}
            >
              <SteepCard style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between', height: '100%', flex: 1 }}>
                <div>
                  <h3 style={{ fontSize: '18px', fontWeight: 500, color: 'var(--color-ink)', margin: 0 }}>
                    Job Seekers
                  </h3>
                  <div style={{ display: 'flex', alignItems: 'baseline', margin: 'var(--spacing-12) 0' }}>
                    <span style={{ fontSize: '36px', fontWeight: 500, color: 'var(--color-ink)' }}>Free</span>
                    <span style={{ fontSize: 'var(--text-caption)', color: 'var(--color-ash)', marginLeft: 'var(--spacing-8)' }}>forever</span>
                  </div>
                  <p style={{ fontSize: 'var(--text-caption)', color: 'var(--color-ash)', lineHeight: 'var(--leading-normal)', margin: 0 }}>
                    Build a verified identity, upload up to 3 resumes, and view match alignment scoring across all active roles.
                  </p>
                </div>
                <div style={{ marginTop: 'var(--spacing-24)' }}>
                  <SteepButton variant="secondary" block to="/register">
                    Create Free Profile
                  </SteepButton>
                </div>
              </SteepCard>
            </motion.div>

            {/* Recruiter Plan */}
            <motion.div
              whileHover={{ y: -3, scale: 1.015 }}
              transition={{ duration: 0.25, ease: 'easeOut' }}
              style={{ display: 'flex', flexDirection: 'column', height: '100%' }}
            >
              <SteepCard style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between', height: '100%', flex: 1, borderColor: 'var(--color-rust)' }}>
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <h3 style={{ fontSize: '18px', fontWeight: 500, color: 'var(--color-ink)', margin: 0 }}>
                      Recruiter Workspace
                    </h3>
                    <SteepBadge variant="success">Active</SteepBadge>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'baseline', margin: 'var(--spacing-12) 0' }}>
                    <span style={{ fontSize: '36px', fontWeight: 500, color: 'var(--color-ink)' }}>$49</span>
                    <span style={{ fontSize: 'var(--text-caption)', color: 'var(--color-ash)', marginLeft: 'var(--spacing-8)' }}>/ month per active job</span>
                  </div>
                  <p style={{ fontSize: 'var(--text-caption)', color: 'var(--color-ash)', lineHeight: 'var(--leading-normal)', margin: 0 }}>
                    Post jobs, access unlimited matching candidates, review risk/authenticity evidence metrics, and manage custom pipeline stages.
                  </p>
                </div>
                <div style={{ marginTop: 'var(--spacing-24)' }}>
                  <SteepButton variant="primary" block to="/register" style={{ background: 'var(--color-ink)', color: 'var(--color-pure-white)' }}>
                    Get Started
                  </SteepButton>
                </div>
              </SteepCard>
            </motion.div>
          </div>
        </div>
      </motion.section>

      {/* Trust & Factual Metrics */}
      <section style={{
        padding: 'var(--spacing-64) var(--spacing-24)',
        borderBottom: '1px solid var(--border)',
        borderTop: '1px solid var(--border)',
        background: 'var(--color-pure-white)',
        position: 'relative',
        zIndex: 1
      }}>
        <div style={{
          maxWidth: 1200,
          margin: '0 auto',
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
          gap: '24px',
          textAlign: 'center'
        }}>
          <div>
            <div style={{ fontSize: 'var(--text-heading-sm)', fontWeight: 500, color: 'var(--color-rust)' }}>
              $<AnimatedCounter value={49} />
            </div>
            <div style={{ fontSize: '11px', color: 'var(--color-ash)', textTransform: 'uppercase', marginTop: 'var(--spacing-8)', fontWeight: 650, letterSpacing: '0.05em' }}>
              Per Month Per Active Job
            </div>
          </div>
          <div>
            <div style={{ fontSize: 'var(--text-heading-sm)', fontWeight: 500, color: 'var(--color-ink)' }}>
              <AnimatedCounter value={3} />
            </div>
            <div style={{ fontSize: '11px', color: 'var(--color-ash)', textTransform: 'uppercase', marginTop: 'var(--spacing-8)', fontWeight: 650, letterSpacing: '0.05em' }}>
              Resumes Max Per Candidate
            </div>
          </div>
          <div>
            <div style={{ fontSize: 'var(--text-heading-sm)', fontWeight: 500, color: 'var(--color-ink)' }}>
              <AnimatedCounter value={100} />%
            </div>
            <div style={{ fontSize: '11px', color: 'var(--color-ash)', textTransform: 'uppercase', marginTop: 'var(--spacing-8)', fontWeight: 650, letterSpacing: '0.05em' }}>
              Mandatory OTP Verification
            </div>
          </div>
          <div>
            <div style={{ fontSize: 'var(--text-heading-sm)', fontWeight: 500, color: 'var(--color-ink)' }}>
              <AnimatedCounter value={activeJobsCount} />
            </div>
            <div style={{ fontSize: '11px', color: 'var(--color-ash)', textTransform: 'uppercase', marginTop: 'var(--spacing-8)', fontWeight: 650, letterSpacing: '0.05em' }}>
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
          padding: 'var(--spacing-96) var(--spacing-24)',
          position: 'relative',
          zIndex: 1
        }}
      >
        <div style={{ maxWidth: 800, margin: '0 auto', textAlign: 'center' }}>
          <span style={{ fontSize: 10, color: 'var(--color-rust)', letterSpacing: '0.05em', textTransform: 'uppercase' }}>
            Our Philosophy
          </span>
          <h2 className="font-signifier" style={{ fontSize: 'var(--text-heading-sm)', fontWeight: 500, color: 'var(--color-ink)', marginTop: 'var(--spacing-8)', marginBottom: 'var(--spacing-16)' }}>
            Trust Over Volume
          </h2>
          <p style={{ fontSize: 'var(--text-body)', color: 'var(--color-ash)', lineHeight: 'var(--leading-normal)', marginInline: 'auto', maxWidth: 640 }}>
            SmartOnboard is built to combat the friction of application spam. We don't optimize for vanity volume. We optimize for credential verification, objective skills verification, and robust signals so that recruiters can discover matches they can trust.
          </p>
        </div>
      </motion.section>

      {/* Footer */}
      <footer style={{
        borderTop: '1px solid var(--border)',
        padding: 'var(--spacing-40) var(--spacing-24)',
        textAlign: 'center',
        position: 'relative',
        zIndex: 1,
        background: 'var(--color-pure-white)'
      }}>
        <div style={{
          maxWidth: 1200,
          margin: '0 auto',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: '16px'
        }}>
          <div style={{ fontSize: 12, fontWeight: 600, letterSpacing: '0.05em', color: 'var(--color-ink)' }}>
            SMARTONBOARD
          </div>
          <div style={{ fontSize: 11, color: 'var(--color-ash)', display: 'flex', gap: '12px', justifyContent: 'center' }}>
            <Link to="/login" style={{ color: 'var(--color-ash)' }}>Login</Link>
            <span>&bull;</span>
            <Link to="/register" style={{ color: 'var(--color-ash)' }}>Register</Link>
            <span>&bull;</span>
            <a href="#features" onClick={(e) => handleScrollTo(e, 'features')} style={{ color: 'var(--color-ash)' }}>Features</a>
            <span>&bull;</span>
            <a href="#solutions" onClick={(e) => handleScrollTo(e, 'solutions')} style={{ color: 'var(--color-ash)' }}>Solutions</a>
            <span>&bull;</span>
            <a href="#pricing" onClick={(e) => handleScrollTo(e, 'pricing')} style={{ color: 'var(--color-ash)' }}>Pricing</a>
          </div>
          <p style={{ fontSize: 11, color: 'var(--color-ash)', marginTop: '8px' }}>
            &copy; 2026 SmartOnboard. All rights reserved. Built with verification integrity.
          </p>
        </div>
      </footer>
    </div>
  )
}

