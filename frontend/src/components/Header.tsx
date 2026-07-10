import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import RecruiterNotificationBell from './RecruiterNotificationBell'

export default function Header() {
  const { pathname } = useLocation()
  const navigate = useNavigate()
  const { user, logout } = useAuth()
  const isHome = pathname === '/'
  const isDashboard = pathname === '/dashboard'

  return (
    <header className="app-header">
      <div className="header-inner">
        <Link to="/" className="brand" aria-label="SmartOnboard home">
          <span className="brand-mark" aria-hidden="true">
            <svg viewBox="0 0 14 14" fill="none">
              <path
                d="M3 7.5L6 10.5L11 4"
                stroke="white"
                strokeWidth="1.75"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </span>
          <span>SmartOnboard</span>
        </Link>

        <nav className="header-nav" aria-label="Primary">
          <Link to="/" className={`nav-link ${isHome ? 'nav-link--active' : ''}`}>
            Product
          </Link>
          {user && (
            <Link to="/dashboard" className={`nav-link ${isDashboard ? 'nav-link--active' : ''}`}>
              Pipeline
            </Link>
          )}
        </nav>

        <div className="header-actions">
          {user ? (
            <>
              <RecruiterNotificationBell />
              <span className="text-secondary" style={{ fontSize: 'var(--text-sm)', marginRight: 'var(--space-2)', marginLeft: '8px' }}>
                {user.full_name}
              </span>
              <button
                type="button"
                className="btn btn--ghost btn--sm"
                onClick={() => {
                  logout()
                  navigate('/login')
                }}
              >
                Sign out
              </button>
            </>
          ) : (
            <>
              <Link to="/login" className="btn btn--ghost btn--sm">Sign in</Link>
              <Link to="/register" className="btn btn--primary btn--sm">Get started</Link>
            </>
          )}
        </div>
      </div>
    </header>
  )
}
