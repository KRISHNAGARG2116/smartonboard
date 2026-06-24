import { Link, useNavigate } from 'react-router-dom'

export default function Register() {
  const navigate = useNavigate()

  return (
    <div style={{
      minHeight: '100vh',
      background: 'var(--bg)',
      color: 'var(--text)',
      fontFamily: "var(--font-sans)",
      display: 'flex',
      flexDirection: 'column'
    }}>
      {/* Navbar */}
      <nav style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        height: 'var(--header-h)',
        padding: '0 var(--space-6)',
        borderBottom: '1px solid var(--border)',
      }}>
        <Link to="/" style={{ fontSize: 18, fontWeight: 500, color: 'var(--text)', textDecoration: 'none', letterSpacing: '0.04em' }}>
          SmartOnboard
        </Link>
        <Link to="/login" style={{ fontSize: 12, fontWeight: 400, color: 'var(--text-secondary)', textDecoration: 'none' }}>
          Already have an account? Login
        </Link>
      </nav>

      {/* Main Container */}
      <div style={{
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 'var(--space-10) var(--space-6)',
        maxWidth: 1000,
        margin: '0 auto',
        width: '100%'
      }}>
        <div style={{ textAlign: 'center', marginBottom: 'var(--space-10)' }}>
          <span style={{
            fontSize: 10,
            fontWeight: 500,
            color: 'var(--text-secondary)',
            letterSpacing: '0.1em',
            textTransform: 'uppercase'
          }}>
            Account Gateway
          </span>
          <h1 style={{
            fontSize: 'var(--text-3xl)',
            fontWeight: 500,
            lineHeight: 'var(--leading-tight)',
            marginTop: 'var(--space-2)',
            color: 'var(--text)'
          }}>
            Join SmartOnboard
          </h1>
          <p style={{
            fontSize: 'var(--text-base)',
            color: 'var(--text-secondary)',
            marginTop: 'var(--space-3)',
            maxWidth: 480,
            marginInline: 'auto'
          }}>
            Create a verified account. Post job roles or search for opportunities with objective skills matching metrics.
          </p>
        </div>

        {/* Card Layout */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
          gap: 'var(--space-6)',
          width: '100%',
          maxWidth: 800
        }}>
          {/* Recruiter / Hiring Card */}
          <div className="card gateway-card" style={{
            padding: 'var(--card-padding)',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between',
            minHeight: 260,
          }}>
            <div>
              <span style={{ fontSize: 10, fontWeight: 500, color: 'var(--text-secondary)', letterSpacing: '0.05em', textTransform: 'uppercase' }}>
                Hiring Workspace
              </span>
              <h2 style={{ fontSize: 'var(--text-xl)', fontWeight: 500, margin: 'var(--space-2) 0 var(--space-3)', color: 'var(--text)' }}>
                Recruiter & Hiring Team
              </h2>
              <p style={{ fontSize: 'var(--text-sm)', lineHeight: 'var(--leading-normal)', color: 'var(--text-secondary)' }}>
                Establish your workspace. Post active openings and leverage resume parsing match statistics to filter and track candidates easily.
              </p>
            </div>
            <button
              onClick={() => navigate('/recruiter/register')}
              className="btn btn--primary"
              style={{
                width: '100%',
                marginTop: 'var(--space-6)',
                cursor: 'pointer'
              }}
            >
              Register Recruiter Workspace
            </button>
          </div>

          {/* Candidate / Job Seeker Card */}
          <div className="card gateway-card" style={{
            padding: 'var(--card-padding)',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between',
            minHeight: 260,
          }}>
            <div>
              <span style={{ fontSize: 10, fontWeight: 500, color: 'var(--text-secondary)', letterSpacing: '0.05em', textTransform: 'uppercase' }}>
                Job Seeker Portal
              </span>
              <h2 style={{ fontSize: 'var(--text-xl)', fontWeight: 500, margin: 'var(--space-2) 0 var(--space-3)', color: 'var(--text)' }}>
                Candidate & Applicant
              </h2>
              <p style={{ fontSize: 'var(--text-sm)', lineHeight: 'var(--leading-normal)', color: 'var(--text-secondary)' }}>
                Build your verified profile, upload up to 3 resumes, and view real-time match scores against active job openings.
              </p>
            </div>
            <button
              onClick={() => navigate('/candidate/register')}
              className="btn btn--secondary"
              style={{
                width: '100%',
                marginTop: 'var(--space-6)',
                cursor: 'pointer'
              }}
            >
              Register Candidate Profile
            </button>
          </div>
        </div>

        {/* Back Link */}
        <Link to="/" style={{
          marginTop: 'var(--space-10)',
          fontSize: 'var(--text-sm)',
          color: 'var(--color-burnt-sienna)',
          textDecoration: 'underline',
          textUnderlineOffset: 3
        }}>
          Back to home page
        </Link>
      </div>
    </div>
  )
}
