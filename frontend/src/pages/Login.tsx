import { Link, useNavigate } from 'react-router-dom'

export default function Login() {
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
        <Link to="/register" style={{ fontSize: 12, fontWeight: 400, color: 'var(--text-secondary)', textDecoration: 'none' }}>
          Need an account? Register
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
            Choose Account Type
          </h1>
          <p style={{
            fontSize: 'var(--text-base)',
            color: 'var(--text-secondary)',
            marginTop: 'var(--space-3)',
            maxWidth: 480,
            marginInline: 'auto'
          }}>
            Sign in to access your dashboard. Choose whether you are managing pipelines or looking for verified matching jobs.
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
          <div style={{
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius-cards)',
            padding: 'var(--card-padding)',
            background: 'transparent',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between',
            minHeight: 260,
            transition: 'border-color var(--duration-fast)'
          }}
          className="gateway-card"
          >
            <div>
              <span style={{ fontSize: 10, fontWeight: 500, color: 'var(--text-secondary)', letterSpacing: '0.05em', textTransform: 'uppercase' }}>
                Hiring Workspace
              </span>
              <h2 style={{ fontSize: 'var(--text-xl)', fontWeight: 500, margin: 'var(--space-2) 0 var(--space-3)', color: 'var(--text)' }}>
                Recruiter & Hiring Team
              </h2>
              <p style={{ fontSize: 'var(--text-sm)', lineHeight: 'var(--leading-normal)', color: 'var(--text-secondary)' }}>
                Publish active listings, screen applicants, evaluate risk & evidence scores, and coordinate interviews in your pipeline dashboard.
              </p>
            </div>
            <button
              onClick={() => navigate('/recruiter/login')}
              className="btn btn--primary"
              style={{
                width: '100%',
                marginTop: 'var(--space-6)',
                backgroundColor: 'var(--color-dark-cork)',
                color: 'var(--color-warm-cream)',
                border: 'none',
                cursor: 'pointer'
              }}
            >
              Sign In as Recruiter
            </button>
          </div>

          {/* Candidate / Job Seeker Card */}
          <div style={{
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius-cards)',
            padding: 'var(--card-padding)',
            background: 'transparent',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between',
            minHeight: 260,
            transition: 'border-color var(--duration-fast)'
          }}
          className="gateway-card"
          >
            <div>
              <span style={{ fontSize: 10, fontWeight: 500, color: 'var(--text-secondary)', letterSpacing: '0.05em', textTransform: 'uppercase' }}>
                Job Seeker Portal
              </span>
              <h2 style={{ fontSize: 'var(--text-xl)', fontWeight: 500, margin: 'var(--space-2) 0 var(--space-3)', color: 'var(--text)' }}>
                Candidate & Applicant
              </h2>
              <p style={{ fontSize: 'var(--text-sm)', lineHeight: 'var(--leading-normal)', color: 'var(--text-secondary)' }}>
                Upload up to 3 resumes, verify your profile with SMS OTP, track skill matching statistics, and review pending interviews.
              </p>
            </div>
            <button
              onClick={() => navigate('/candidate/login')}
              className="btn btn--secondary"
              style={{
                width: '100%',
                marginTop: 'var(--space-6)',
                border: '1px solid var(--border)',
                color: 'var(--color-warm-cream)',
                background: 'transparent',
                cursor: 'pointer'
              }}
            >
              Sign In as Candidate
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
