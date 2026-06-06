import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import heroImg from '../assets/oryzo_hero.png'
import corkImg from '../assets/oryzo_cork_render.png'

export default function Landing() {
  const { user } = useAuth()
  const [scrollOpacity, setScrollOpacity] = useState(1)

  // Fade scroll prompt as user scrolls
  useEffect(() => {
    const handleScroll = () => {
      const fade = Math.max(0, 1 - window.scrollY / 300)
      setScrollOpacity(fade)
    }
    window.addEventListener('scroll', handleScroll, { passive: true })
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  return (
    <div style={{ background: '#100904', color: '#ffedd7', minHeight: '100vh' }}>
      {/* ════════════════════════════════════════════
          SECTION 1 — HERO (full viewport)
          ════════════════════════════════════════════ */}
      <section
        style={{
          position: 'relative',
          width: '100%',
          height: '100vh',
          minHeight: '600px',
          backgroundImage: `url(${heroImg})`,
          backgroundSize: 'cover',
          backgroundPosition: 'center',
          backgroundRepeat: 'no-repeat',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        {/* Dark overlay */}
        <div
          style={{
            position: 'absolute',
            inset: 0,
            background: 'rgba(16, 9, 4, 0.72)',
            zIndex: 1,
          }}
        />

        {/* Top Navigation Bar */}
        <nav
          style={{
            position: 'relative',
            zIndex: 10,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '0 40px',
            height: '56px',
            borderBottom: '1px solid #40372e',
            background: 'transparent',
          }}
        >
          {/* Wordmark */}
          <Link
            to="/"
            style={{
              fontSize: '15px',
              fontWeight: 500,
              color: '#ffedd7',
              textDecoration: 'none',
              letterSpacing: '0.12em',
              fontFamily: "'Plus Jakarta Sans', sans-serif",
            }}
          >
            ORYZO
          </Link>

          {/* Right nav items */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '24px' }}>
            <a
              href="#hero"
              style={{
                fontSize: '12px',
                fontWeight: 400,
                color: '#ffedd7',
                textDecoration: 'none',
                letterSpacing: '0.06em',
                fontFamily: "'Plus Jakarta Sans', sans-serif",
              }}
            >
              INTRO
            </a>
            <a
              href="#features"
              style={{
                fontSize: '12px',
                fontWeight: 400,
                color: '#ffedd7',
                textDecoration: 'none',
                letterSpacing: '0.06em',
                fontFamily: "'Plus Jakarta Sans', sans-serif",
              }}
            >
              FEATURES
            </a>
            <a
              href="#metrics"
              style={{
                fontSize: '12px',
                fontWeight: 400,
                color: '#ffedd7',
                textDecoration: 'none',
                letterSpacing: '0.06em',
                fontFamily: "'Plus Jakarta Sans', sans-serif",
              }}
            >
              PRODUCT
            </a>
            <a
              href="#cta"
              style={{
                fontSize: '12px',
                fontWeight: 400,
                color: '#ffedd7',
                textDecoration: 'none',
                letterSpacing: '0.06em',
                fontFamily: "'Plus Jakarta Sans', sans-serif",
              }}
            >
              CONTACT
            </a>

            {/* Divider */}
            <div
              style={{
                width: '1px',
                height: '20px',
                background: '#40372e',
              }}
            />

            {/* Auth links */}
            {user ? (
              <Link
                to="/dashboard"
                style={{
                  fontSize: '12px',
                  fontWeight: 400,
                  color: '#ffedd7',
                  textDecoration: 'none',
                  letterSpacing: '0.06em',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                }}
              >
                <span
                  style={{
                    width: '24px',
                    height: '24px',
                    borderRadius: '50%',
                    border: '1px solid #40372e',
                    display: 'grid',
                    placeItems: 'center',
                    fontSize: '10px',
                    fontWeight: 500,
                    color: '#ffedd7',
                  }}
                >
                  {(user as any).full_name?.[0]?.toUpperCase() || 'U'}
                </span>
                DASHBOARD
              </Link>
            ) : (
              <>
                <Link
                  to="/login"
                  style={{
                    fontSize: '12px',
                    fontWeight: 400,
                    color: '#ffedd7',
                    textDecoration: 'none',
                    letterSpacing: '0.06em',
                  }}
                >
                  Sign In
                </Link>
                <Link
                  to="/register"
                  style={{
                    fontSize: '12px',
                    fontWeight: 500,
                    color: '#ffedd7',
                    textDecoration: 'none',
                    letterSpacing: '0.06em',
                    padding: '6px 16px',
                    border: '1px solid #ffedd7',
                    borderRadius: '22.5px',
                  }}
                >
                  Get Started
                </Link>
              </>
            )}
          </div>
        </nav>

        {/* Hero Content */}
        <div
          id="hero"
          style={{
            position: 'relative',
            zIndex: 10,
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between',
            padding: '80px 40px 40px',
          }}
        >
          {/* Top area: headline left, body copy center-right */}
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'flex-start',
              gap: '60px',
              flexWrap: 'wrap',
            }}
          >
            {/* Giant headline */}
            <div>
              <h1
                style={{
                  fontSize: '51px',
                  fontWeight: 500,
                  lineHeight: 0.9,
                  color: '#ffedd7',
                  maxWidth: '12ch',
                  margin: 0,
                  fontFamily: "'Plus Jakarta Sans', sans-serif",
                }}
              >
                Better Applicants.
                <br />
                Better Hiring.
              </h1>

              {/* CTA buttons below headline */}
              <div
                style={{
                  display: 'flex',
                  gap: '16px',
                  marginTop: '40px',
                  flexWrap: 'wrap',
                }}
              >
                <Link
                  to="/register"
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    background: '#382416',
                    color: '#ffedd7',
                    borderRadius: '36px',
                    padding: '14px 24px',
                    fontSize: '14px',
                    fontWeight: 500,
                    textDecoration: 'none',
                    border: 'none',
                    fontFamily: "'Plus Jakarta Sans', sans-serif",
                    letterSpacing: '0.02em',
                  }}
                >
                  Start Hiring
                </Link>
                <Link
                  to="/candidate/login"
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    background: 'transparent',
                    color: '#ffedd7',
                    borderRadius: '22.5px',
                    padding: '14px 24px',
                    fontSize: '14px',
                    fontWeight: 500,
                    textDecoration: 'none',
                    border: '1px solid #ffedd7',
                    fontFamily: "'Plus Jakarta Sans', sans-serif",
                    letterSpacing: '0.02em',
                  }}
                >
                  I'm a Candidate
                </Link>
              </div>
            </div>

            {/* Body copy center-right */}
            <p
              style={{
                fontSize: '18px',
                fontWeight: 400,
                lineHeight: 1.2,
                color: '#ffedd7',
                maxWidth: '420px',
                margin: 0,
                marginTop: '20px',
                fontFamily: "'Plus Jakarta Sans', sans-serif",
              }}
            >
              The verified hiring ecosystem that maximizes recruiter trust and
              hiring quality.
            </p>
          </div>

          {/* Bottom area: scroll prompt */}
          <div
            style={{
              display: 'flex',
              justifyContent: 'center',
              alignItems: 'center',
              flexDirection: 'column',
              gap: '8px',
              opacity: scrollOpacity,
              transition: 'opacity 0.3s ease',
            }}
          >
            <span
              style={{
                fontSize: '10px',
                fontWeight: 400,
                color: '#ffedd7',
                letterSpacing: '0.16em',
                fontFamily: "'Plus Jakarta Sans', sans-serif",
              }}
            >
              SCROLL TO CONTINUE
            </span>
            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="#ffedd7"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <polyline points="6 9 12 15 18 9" />
            </svg>
          </div>
        </div>

        {/* Right-edge vertical label */}
        <div
          style={{
            position: 'fixed',
            right: '16px',
            top: '50%',
            transform: 'rotate(90deg)',
            transformOrigin: 'center center',
            zIndex: 10,
            fontSize: '10px',
            fontWeight: 400,
            color: '#6c5f51',
            letterSpacing: '0.12em',
            fontFamily: "'Plus Jakarta Sans', sans-serif",
            pointerEvents: 'none',
          }}
        >
          ORYZO-1 MODEL
        </div>
      </section>

      {/* ════════════════════════════════════════════
          SECTION 2 — FEATURES (full viewport)
          ════════════════════════════════════════════ */}
      <section
        id="features"
        style={{
          position: 'relative',
          width: '100%',
          minHeight: '100vh',
          background: '#100904',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          alignItems: 'center',
          padding: '80px 40px',
        }}
      >
        {/* Cork render image centered */}
        <div
          style={{
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            flex: 1,
            width: '100%',
          }}
        >
          <img
            src={corkImg}
            alt="ORYZO 3D cork render"
            style={{
              width: '55vw',
              maxWidth: '800px',
              height: 'auto',
              objectFit: 'contain',
            }}
          />
        </div>

        {/* Bottom content: headline left, body right */}
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'flex-end',
            width: '100%',
            maxWidth: '1200px',
            gap: '60px',
            flexWrap: 'wrap',
            marginTop: '60px',
          }}
        >
          <h2
            style={{
              fontSize: '41px',
              fontWeight: 500,
              lineHeight: 1.0,
              color: '#ffedd7',
              margin: 0,
              maxWidth: '14ch',
              fontFamily: "'Plus Jakarta Sans', sans-serif",
            }}
          >
            Verified Hiring
            <br />
            Ecosystem
          </h2>

          <div
            style={{
              maxWidth: '420px',
              display: 'flex',
              flexDirection: 'column',
              gap: '20px',
            }}
          >
            <p
              style={{
                fontSize: '18px',
                fontWeight: 400,
                lineHeight: 1.2,
                color: '#ffedd7',
                margin: 0,
                fontFamily: "'Plus Jakarta Sans', sans-serif",
              }}
            >
              Batch resume screening — upload multiple PDFs and compare
              candidates ranked by fit score against your job description.
            </p>
            <p
              style={{
                fontSize: '18px',
                fontWeight: 400,
                lineHeight: 1.2,
                color: '#ffedd7',
                margin: 0,
                fontFamily: "'Plus Jakarta Sans', sans-serif",
              }}
            >
              Structured hiring decisions — every candidate gets a Hire,
              Interview, or Reject recommendation with reasoning.
            </p>
            <p
              style={{
                fontSize: '18px',
                fontWeight: 400,
                lineHeight: 1.2,
                color: '#ffedd7',
                margin: 0,
                fontFamily: "'Plus Jakarta Sans', sans-serif",
              }}
            >
              Trusted verification — closed ecosystem where every participant is
              verified for recruiter confidence.
            </p>
          </div>
        </div>
      </section>

      {/* ════════════════════════════════════════════
          SECTION 3 — METRICS
          ════════════════════════════════════════════ */}
      <section
        id="metrics"
        style={{
          width: '100%',
          background: '#100904',
          borderTop: '1px dashed #40372e',
          borderBottom: '1px dashed #40372e',
        }}
      >
        <div
          style={{
            display: 'flex',
            maxWidth: '1200px',
            margin: '0 auto',
            padding: '60px 40px',
          }}
        >
          {/* Metric 1 */}
          <div
            style={{
              flex: 1,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: '8px',
            }}
          >
            <span
              style={{
                fontSize: '29px',
                fontWeight: 500,
                lineHeight: 1.09,
                color: '#ffedd7',
                fontFamily: "'Plus Jakarta Sans', sans-serif",
              }}
            >
              5
            </span>
            <span
              style={{
                fontSize: '10px',
                fontWeight: 400,
                lineHeight: 1.2,
                color: '#ffedd7',
                letterSpacing: '0.08em',
                textTransform: 'uppercase',
                fontFamily: "'Plus Jakarta Sans', sans-serif",
              }}
            >
              AI agents per candidate
            </span>
          </div>

          {/* Dashed divider */}
          <div
            style={{
              width: '1px',
              borderLeft: '1px dashed #40372e',
            }}
          />

          {/* Metric 2 */}
          <div
            style={{
              flex: 1,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: '8px',
            }}
          >
            <span
              style={{
                fontSize: '29px',
                fontWeight: 500,
                lineHeight: 1.09,
                color: '#ffedd7',
                fontFamily: "'Plus Jakarta Sans', sans-serif",
              }}
            >
              $49
            </span>
            <span
              style={{
                fontSize: '10px',
                fontWeight: 400,
                lineHeight: 1.2,
                color: '#ffedd7',
                letterSpacing: '0.08em',
                textTransform: 'uppercase',
                fontFamily: "'Plus Jakarta Sans', sans-serif",
              }}
            >
              Per active job / month
            </span>
          </div>

          {/* Dashed divider */}
          <div
            style={{
              width: '1px',
              borderLeft: '1px dashed #40372e',
            }}
          />

          {/* Metric 3 */}
          <div
            style={{
              flex: 1,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: '8px',
            }}
          >
            <span
              style={{
                fontSize: '29px',
                fontWeight: 500,
                lineHeight: 1.09,
                color: '#ffedd7',
                fontFamily: "'Plus Jakarta Sans', sans-serif",
              }}
            >
              3
            </span>
            <span
              style={{
                fontSize: '10px',
                fontWeight: 400,
                lineHeight: 1.2,
                color: '#ffedd7',
                letterSpacing: '0.08em',
                textTransform: 'uppercase',
                fontFamily: "'Plus Jakarta Sans', sans-serif",
              }}
            >
              Max resumes per candidate
            </span>
          </div>
        </div>
      </section>

      {/* ════════════════════════════════════════════
          SECTION 4 — CTA FOOTER
          ════════════════════════════════════════════ */}
      <section
        id="cta"
        style={{
          width: '100%',
          background: '#100904',
          padding: '100px 40px 60px',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          textAlign: 'center',
        }}
      >
        <h2
          style={{
            fontSize: '29px',
            fontWeight: 500,
            lineHeight: 1.09,
            color: '#ffedd7',
            margin: 0,
            fontFamily: "'Plus Jakarta Sans', sans-serif",
          }}
        >
          Ready to hire with confidence?
        </h2>
        <p
          style={{
            fontSize: '14px',
            fontWeight: 400,
            lineHeight: 1.33,
            color: '#6c5f51',
            margin: '16px 0 32px',
            maxWidth: '420px',
            fontFamily: "'Plus Jakarta Sans', sans-serif",
          }}
        >
          Upload resumes, add a job description, and get ranked results powered
          by five AI agents working in parallel.
        </p>
        <Link
          to="/dashboard"
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            background: 'transparent',
            color: '#ffedd7',
            borderRadius: '22.5px',
            padding: '14px 28px',
            fontSize: '14px',
            fontWeight: 500,
            textDecoration: 'none',
            border: '1px solid #dc5000',
            fontFamily: "'Plus Jakarta Sans', sans-serif",
            letterSpacing: '0.02em',
          }}
        >
          Open Recruiter Dashboard
        </Link>

        {/* Dashed divider */}
        <div
          style={{
            width: '100%',
            maxWidth: '1200px',
            borderTop: '1px dashed #40372e',
            marginTop: '80px',
            paddingTop: '24px',
          }}
        >
          <span
            style={{
              fontSize: '10px',
              fontWeight: 400,
              color: '#6c5f51',
              letterSpacing: '0.08em',
              fontFamily: "'Plus Jakarta Sans', sans-serif",
            }}
          >
            ORYZO AI · Verified Hiring
          </span>
        </div>
      </section>
    </div>
  )
}
