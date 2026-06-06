import { Link } from 'react-router-dom'

export default function Landing() {
  return (
    <div style={{
      minHeight: '100vh',
      background: '#100904',
      color: '#ffedd7',
      fontFamily: "'Plus Jakarta Sans', sans-serif",
      position: 'relative',
      overflowX: 'hidden'
    }}>
      {/* Rotated fixed label */}
      <div style={{
        position: 'fixed',
        right: -30,
        top: '50%',
        transform: 'rotate(90deg)',
        fontSize: 10,
        fontWeight: 500,
        letterSpacing: '0.1em',
        color: '#6c5f51',
        zIndex: 10,
        pointerEvents: 'none'
      }}>
        ORYZO-1 MODEL
      </div>

      {/* Top Navbar */}
      <nav style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        height: 56,
        padding: '0 24px',
        borderBottom: '1px solid #40372e',
      }}>
        <div style={{ fontSize: 18, fontWeight: 500, letterSpacing: '0.04em' }}>
          ORYZO
        </div>
        <div style={{ display: 'flex', gap: 24 }}>
          <Link to="/recruiter/login" style={{ fontSize: 12, fontWeight: 400, color: '#ffedd7', textDecoration: 'none' }}>
            I'M HIRING
          </Link>
          <Link to="/candidate/login" style={{ fontSize: 12, fontWeight: 400, color: '#ffedd7', textDecoration: 'none' }}>
            I'M A CANDIDATE
          </Link>
        </div>
      </nav>

      {/* Hero Section (Full Viewport) */}
      <div style={{
        minHeight: 'calc(100vh - 56px)',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        padding: '80px 24px',
        maxWidth: 1200,
        margin: '0 auto',
        boxSizing: 'border-box'
      }}>
        <div style={{
          display: 'grid',
          gridTemplateColumns: '1fr',
          gap: 48,
          alignItems: 'center'
        }}>
          {/* Main Copy */}
          <div>
            <h1 style={{
              fontSize: 51,
              fontWeight: 500,
              lineHeight: 0.9,
              letterSpacing: '-0.03em',
              margin: 0,
              color: '#ffedd7',
              maxWidth: '15ch'
            }}>
              Screen. Match.<br/>Interview. Recruit.
            </h1>
            <p style={{
              fontSize: 18,
              lineHeight: 1.3,
              color: '#ffedd7',
              marginTop: 24,
              maxWidth: 480
            }}>
              The verified hiring ecosystem designed strictly for resume screening, AI candidate matching, applicant verification, interview scheduling, and recruiting workspace coordination.
            </p>
          </div>

          {/* Gateway Panels - First Viewport */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
            gap: 24,
            marginTop: 24
          }}>
            {/* Recruiter Gateway */}
            <div style={{
              border: '1px solid #ffedd7',
              borderRadius: 12,
              padding: 32,
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
              minHeight: 220,
              background: 'transparent'
            }}>
              <div>
                <span style={{ fontSize: 10, fontWeight: 500, color: '#6c5f51', letterSpacing: '0.05em', textTransform: 'uppercase' }}>
                  For Workspaces
                </span>
                <h2 style={{ fontSize: 24, fontWeight: 500, margin: '8px 0 12px', color: '#ffedd7' }}>
                  I'm Hiring
                </h2>
                <p style={{ fontSize: 14, lineHeight: 1.33, color: '#6c5f51', margin: 0 }}>
                  Publish active job listings, execute automated resume parser matching, coordinate pipelines, and invite recruiting team members.
                </p>
              </div>
              <div style={{ marginTop: 24 }}>
                <Link to="/recruiter/register" style={{
                  display: 'inline-block',
                  padding: '12px 24px',
                  background: '#382416',
                  color: '#ffedd7',
                  borderRadius: 36,
                  fontSize: 14,
                  fontWeight: 500,
                  textDecoration: 'none',
                  textAlign: 'center'
                }}>
                  Start Recruiting
                </Link>
              </div>
            </div>

            {/* Candidate Gateway */}
            <div style={{
              border: '1px solid #ffedd7',
              borderRadius: 12,
              padding: 32,
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
              minHeight: 220,
              background: 'transparent'
            }}>
              <div>
                <span style={{ fontSize: 10, fontWeight: 500, color: '#6c5f51', letterSpacing: '0.05em', textTransform: 'uppercase' }}>
                  For Job Seekers
                </span>
                <h2 style={{ fontSize: 24, fontWeight: 500, margin: '8px 0 12px', color: '#ffedd7' }}>
                  I'm Looking For A Job
                </h2>
                <p style={{ fontSize: 14, lineHeight: 1.33, color: '#6c5f51', margin: 0 }}>
                  Upload up to 3 resumes, verify your email and phone OTP status, review matching skills metrics, and apply to job openings.
                </p>
              </div>
              <div style={{ marginTop: 24 }}>
                <Link to="/candidate/register" style={{
                  display: 'inline-block',
                  padding: '12px 24px',
                  background: 'transparent',
                  color: '#ffedd7',
                  border: '1px solid #ffedd7',
                  borderRadius: 22.5,
                  fontSize: 14,
                  fontWeight: 500,
                  textDecoration: 'none',
                  textAlign: 'center'
                }}>
                  Create Profile
                </Link>
              </div>
            </div>
          </div>
        </div>

        {/* Scroll prompt */}
        <div style={{
          marginTop: 64,
          display: 'flex',
          justifyContent: 'center',
          fontSize: 10,
          color: '#6c5f51',
          letterSpacing: '0.1em'
        }}>
          SCROLL TO EXPLORE VALUE PIPELINES
        </div>
      </div>

      {/* Feature Value Showcase Section */}
      <div style={{
        borderTop: '1px dashed #40372e',
        background: '#100904',
        padding: '80px 24px'
      }}>
        <div style={{ maxWidth: 1200, margin: '0 auto' }}>
          <span style={{ fontSize: 10, fontWeight: 500, color: '#6c5f51', letterSpacing: '0.05em', textTransform: 'uppercase' }}>
            System Capacities
          </span>
          <h2 style={{ fontSize: 41, fontWeight: 500, letterSpacing: '-0.02em', margin: '8px 0 48px' }}>
            Verified Hiring Platform
          </h2>

          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
            gap: 24
          }}>
            {/* Value 1 */}
            <div style={{ borderTop: '1px dashed #40372e', paddingTop: 20 }}>
              <h3 style={{ fontSize: 18, fontWeight: 500, color: '#ffedd7', margin: '0 0 12px' }}>
                AI Match Screening
              </h3>
              <p style={{ fontSize: 14, lineHeight: 1.33, color: '#6c5f51', margin: 0 }}>
                Automatic background resume parsing matches applicant skills directly against the job requirements, reporting precise fit metrics.
              </p>
            </div>

            {/* Value 2 */}
            <div style={{ borderTop: '1px dashed #40372e', paddingTop: 20 }}>
              <h3 style={{ fontSize: 18, fontWeight: 500, color: '#ffedd7', margin: '0 0 12px' }}>
                Verified Credentials
              </h3>
              <p style={{ fontSize: 14, lineHeight: 1.33, color: '#6c5f51', margin: 0 }}>
                Twilio SMS OTP and Email authentication verification codes ensure candidate profile integrity and eliminate application spam.
              </p>
            </div>

            {/* Value 3 */}
            <div style={{ borderTop: '1px dashed #40372e', paddingTop: 20 }}>
              <h3 style={{ fontSize: 18, fontWeight: 500, color: '#ffedd7', margin: '0 0 12px' }}>
                Unified Pipelines
              </h3>
              <p style={{ fontSize: 14, lineHeight: 1.33, color: '#6c5f51', margin: 0 }}>
                Track applicants through customizable hiring boards. Schedule interviews, track sync status logs, and manage team reviews.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Metrics Section */}
      <div style={{
        borderTop: '1px dashed #40372e',
        background: '#100904',
        padding: '40px 24px'
      }}>
        <div style={{
          maxWidth: 1200,
          margin: '0 auto',
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
          gap: 24,
          textAlign: 'center'
        }}>
          <div>
            <div style={{ fontSize: 29, fontWeight: 500, color: '#ffedd7' }}>5</div>
            <div style={{ fontSize: 10, color: '#6c5f51', letterSpacing: '0.05em', textTransform: 'uppercase', marginTop: 4 }}>
              AI agents per candidate
            </div>
          </div>
          <div style={{ borderLeft: '1px dashed #40372e', borderRight: '1px dashed #40372e' }}>
            <div style={{ fontSize: 29, fontWeight: 500, color: '#ffedd7' }}>$49</div>
            <div style={{ fontSize: 10, color: '#6c5f51', letterSpacing: '0.05em', textTransform: 'uppercase', marginTop: 4 }}>
              Per active job/month (Workspace plan)
            </div>
          </div>
          <div>
            <div style={{ fontSize: 29, fontWeight: 500, color: '#ffedd7' }}>3</div>
            <div style={{ fontSize: 10, color: '#6c5f51', letterSpacing: '0.05em', textTransform: 'uppercase', marginTop: 4 }}>
              Max resumes per profile
            </div>
          </div>
        </div>
      </div>

      {/* Footer */}
      <footer style={{
        borderTop: '1px dashed #40372e',
        padding: '32px 24px',
        textAlign: 'center',
        fontSize: 10,
        color: '#6c5f51',
        letterSpacing: '0.05em'
      }}>
        ORYZO AI &bull; VERIFIED HIRING ECOSYSTEM &bull; 2026
      </footer>
    </div>
  )
}
