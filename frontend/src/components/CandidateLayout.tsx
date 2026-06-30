import { useState, useEffect, type ReactNode } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useTheme } from '../context/ThemeContext'
import { fetchCandidateProfile } from '../api'
import AnimatedPage from './AnimatedPage'
import { AnimatePresence } from 'framer-motion'
import SteepSidebarItem from './design-system/SteepSidebarItem'

interface CandidateLayoutProps {
  children: ReactNode
}

export default function CandidateLayout({ children }: CandidateLayoutProps) {
  const { pathname } = useLocation()
  const navigate = useNavigate()
  const { user, logout } = useAuth()
  const { resolvedTheme, toggleTheme } = useTheme()

  const [profile, setProfile] = useState<{ email_verified: boolean; phone_verified: boolean } | null>(null)

  useEffect(() => {
    fetchCandidateProfile()
      .then(data => {
        if (data && data.profile) {
          setProfile(data.profile)
        }
      })
      .catch(() => {})
  }, [pathname])

  const [isMobileOpen, setIsMobileOpen] = useState(false)
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false)

  // Close menus on path change
  useEffect(() => {
    setIsMobileOpen(false)
    setIsUserMenuOpen(false)
  }, [pathname])

  // Close menus on window resize if larger than mobile breakpoint
  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth > 900) {
        setIsMobileOpen(false)
      }
    }
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  const handleLogout = () => {
    logout()
    navigate('/candidate/login')
  }

  const navItems = [
    {
      name: 'Dashboard',
      path: '/candidate/dashboard',
      icon: (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
          <rect x="3" y="3" width="7" height="9" rx="1" />
          <rect x="14" y="3" width="7" height="5" rx="1" />
          <rect x="14" y="12" width="7" height="9" rx="1" />
          <rect x="3" y="16" width="7" height="5" rx="1" />
        </svg>
      )
    },
    {
      name: 'Jobs',
      path: '/candidate/jobs',
      icon: (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
          <rect x="2" y="7" width="20" height="14" rx="2" ry="2" />
          <path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16" />
        </svg>
      )
    },
    {
      name: 'Applications',
      path: '/candidate/applications',
      icon: (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
          <polyline points="22 12 16 12 14 15 10 15 8 12 2 12" />
          <path d="M5.45 5.11L2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z" />
        </svg>
      )
    },
    {
      name: 'Interviews',
      path: '/candidate/interviews',
      icon: (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
          <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
          <line x1="16" y1="2" x2="16" y2="6" />
          <line x1="8" y1="2" x2="8" y2="6" />
          <line x1="3" y1="10" x2="21" y2="10" />
        </svg>
      )
    },
    {
      name: 'Resumes',
      path: '/candidate/resumes',
      icon: (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z" />
          <polyline points="14 2 14 8 20 8" />
          <line x1="16" y1="13" x2="8" y2="13" />
          <line x1="16" y1="17" x2="8" y2="17" />
          <line x1="10" y1="9" x2="8" y2="9" />
        </svg>
      )
    },
    {
      name: 'Profile',
      path: '/candidate/profile',
      icon: (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
          <circle cx="12" cy="7" r="4" />
        </svg>
      )
    },
    {
      name: 'Settings',
      path: '/candidate/settings',
      icon: (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="12" r="3" />
          <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
        </svg>
      )
    }
  ]

  return (
    <div
      style={{
        display: 'flex',
        minHeight: '100vh',
        background: 'var(--bg)',
        color: 'var(--text)',
        fontFamily: 'var(--font-sans)',
        transition: 'background var(--duration-normal), color var(--duration-normal)',
      }}
    >
      {/* Sidebar Desktop */}
      <aside
        style={{
          width: '240px',
          background: 'var(--color-fog)',
          borderRight: 'none',
          display: 'flex',
          flexDirection: 'column',
          zIndex: 150,
          position: 'relative',
        }}
        className="candidate-sidebar-desktop"
      >
        {/* Header Logo */}
        <div
          style={{
            height: 'var(--header-h)',
            display: 'flex',
            alignItems: 'center',
            padding: '0 var(--space-5)',
            borderBottom: '1px solid var(--border)',
            gap: 'var(--space-3)',
          }}
        >
          <div
            style={{
              width: '32px',
              height: '32px',
              borderRadius: '6px',
              background: 'var(--color-rust)',
              display: 'grid',
              placeItems: 'center',
              color: 'var(--text)',
              fontWeight: 800,
              fontSize: '14px',
              
            }}
          >
            OR
          </div>
          <div>
            <span style={{ fontSize: '14px', fontWeight: 700, letterSpacing: '-0.02em' }}>SmartOnboard</span>
            <span style={{ display: 'block', fontSize: '9px', fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em', marginTop: '-2px' }}>
              CANDIDATE
            </span>
          </div>
        </div>

        {/* Sidebar Nav Links */}
        <nav
          style={{
            flex: 1,
            padding: 'var(--space-4) var(--space-3)',
            display: 'flex',
            flexDirection: 'column',
            gap: '6px',
            overflowY: 'auto',
          }}
        >
          {navItems.map((item) => (
            <SteepSidebarItem
              key={item.path}
              to={item.path}
              label={item.name}
              icon={item.icon}
              active={pathname === item.path}
            />
          ))}
        </nav>

        {/* Sidebar Footer Logout Button */}
        <div style={{ padding: 'var(--space-4)', borderTop: '1px solid var(--border)' }}>
          <button
            type="button"
            className="btn btn--secondary btn--block"
            onClick={handleLogout}
            style={{ padding: '10px 14px', borderRadius: 'var(--radius-buttons)', fontSize: '13px' }}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" style={{ marginRight: '6px' }}>
              <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
              <polyline points="16 17 21 12 16 7" />
              <line x1="21" y1="12" x2="9" y2="12" />
            </svg>
            Sign Out
          </button>
        </div>
      </aside>

      {/* Sidebar Mobile Drawer */}
      {isMobileOpen && (
        <div
          onClick={() => setIsMobileOpen(false)}
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(16, 9, 4, 0.7)',
            backdropFilter: 'none',
            zIndex: 199,
          }}
        />
      )}
      <aside
        style={{
          width: '240px',
          background: 'var(--color-fog)',
          borderRight: 'none',
          display: 'flex',
          flexDirection: 'column',
          zIndex: 200,
          position: 'fixed',
          top: 0,
          bottom: 0,
          left: isMobileOpen ? 0 : '-240px',
          transition: 'left 250ms cubic-bezier(0.16, 1, 0.3, 1)',
        }}
      >
        <div
          style={{
            height: 'var(--header-h)',
            display: 'flex',
            alignItems: 'center',
            padding: '0 var(--space-5)',
            borderBottom: '1px solid var(--border)',
            gap: 'var(--space-3)',
            justifyContent: 'space-between',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
            <div
              style={{
                width: '32px',
                height: '32px',
                borderRadius: '6px',
                background: 'var(--color-rust)',
                display: 'grid',
                placeItems: 'center',
                color: 'var(--text)',
                fontWeight: 800,
                fontSize: '14px',
              }}
            >
              OR
            </div>
            <div>
              <span style={{ fontSize: '14px', fontWeight: 700 }}>SmartOnboard</span>
              <span style={{ display: 'block', fontSize: '9px', fontWeight: 700, color: 'var(--text-secondary)' }}>CANDIDATE</span>
            </div>
          </div>
          <button
            type="button"
            className="icon-btn"
            onClick={() => setIsMobileOpen(false)}
            aria-label="Close menu"
          >
            ✕
          </button>
        </div>

        <nav
          style={{
            flex: 1,
            padding: 'var(--space-4) var(--space-3)',
            display: 'flex',
            flexDirection: 'column',
            gap: '6px',
            overflowY: 'auto',
          }}
        >
          {navItems.map((item) => (
            <SteepSidebarItem
              key={item.path}
              to={item.path}
              label={item.name}
              icon={item.icon}
              active={pathname === item.path}
            />
          ))}
        </nav>

        <div style={{ padding: 'var(--space-4)', borderTop: '1px solid var(--border)' }}>
          <button
            type="button"
            className="btn btn--secondary btn--block"
            onClick={handleLogout}
          >
            Sign Out
          </button>
        </div>
      </aside>

      {/* Main Content Pane */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0, minHeight: '100vh' }}>
        {/* Sticky Header Top Navigation */}
        <header
          style={{
            position: 'sticky',
            top: 0,
            zIndex: 100,
            height: 'var(--header-h)',
            background: 'var(--bg)',
            borderBottom: '1px solid var(--color-cork-shadow)',
            backdropFilter: 'none',
            transition: 'background var(--duration-normal), border-color var(--duration-normal)',
          }}
        >
          <div
            style={{
              paddingInline: 'var(--space-6)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              height: '100%',
            }}
          >
            {/* Left Header Menu button */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
              <button
                type="button"
                className="icon-btn candidate-hamburger"
                onClick={() => setIsMobileOpen(!isMobileOpen)}
                style={{
                  width: '38px',
                  height: '38px',
                  borderRadius: '10px',
                  background: 'var(--bg-subtle)',
                  border: '1px solid var(--border)',
                }}
                aria-label="Open menu"
              >
                ☰
              </button>
              <h2 style={{ fontSize: 'var(--text-md)', fontWeight: 700, letterSpacing: '-0.01em' }}>
                {pathname === '/candidate/dashboard' && 'Dashboard'}
                {pathname === '/candidate/resumes' && 'Resume Library'}
                {pathname === '/candidate/jobs' && 'Explore Jobs'}
                {pathname === '/candidate/applications' && 'My Applications'}
                {pathname === '/candidate/interviews' && 'My Interviews'}
                {pathname === '/candidate/profile' && 'Profile Settings'}
              </h2>
            </div>

            {/* Right Header User Menu & Theme Toggle */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
              {/* Theme Toggle */}
              <button
                type="button"
                className="icon-btn"
                onClick={toggleTheme}
                style={{
                  width: '38px',
                  height: '38px',
                  borderRadius: '10px',
                  background: 'var(--bg-subtle)',
                  border: '1px solid var(--border)',
                  color: 'var(--text-secondary)',
                }}
                title="Toggle Theme"
              >
                {resolvedTheme === 'light' ? (
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
                    <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
                  </svg>
                ) : (
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
                    <circle cx="12" cy="12" r="5" />
                    <line x1="12" y1="1" x2="12" y2="3" />
                    <line x1="12" y1="21" x2="12" y2="23" />
                    <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" />
                    <line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
                    <line x1="1" y1="12" x2="3" y2="12" />
                    <line x1="21" y1="12" x2="23" y2="12" />
                    <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" />
                    <line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
                  </svg>
                )}
              </button>

              {/* User Menu Dropdown trigger */}
              <div style={{ position: 'relative' }}>
                <button
                  type="button"
                  onClick={() => setIsUserMenuOpen(!isUserMenuOpen)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    padding: '4px',
                    borderRadius: '999px',
                    cursor: 'pointer',
                  }}
                >
                  <div
                    style={{
                      width: '32px',
                      height: '32px',
                      borderRadius: 'var(--radius-avatars)',
                      background: 'var(--color-sky-wash)',
                      display: 'grid',
                      placeItems: 'center',
                      color: 'var(--color-ink)',
                      fontWeight: 500,
                      fontSize: '13px',
                    }}
                  >
                    {user?.full_name ? user.full_name.split(' ').map((n: string) => n[0]).join('').slice(0, 2).toUpperCase() : 'U'}
                  </div>
                </button>

                {isUserMenuOpen && (
                  <>
                    <div
                      onClick={() => setIsUserMenuOpen(false)}
                      style={{ position: 'fixed', inset: 0, zIndex: 180 }}
                    />
                    <div
                      className="card"
                      style={{
                        position: 'absolute',
                        right: 0,
                        top: '46px',
                        width: '240px',
                        zIndex: 181,
                        background: 'var(--color-pure-white)',
                        borderRadius: 'var(--radius-cards)',
                        border: '1px solid var(--border)',
                        padding: 'var(--space-2)',
                      }}
                    >
                      <div
                        style={{
                          padding: '10px 12px',
                          borderBottom: '1px solid var(--border)',
                          marginBottom: '6px',
                        }}
                      >
                        <div style={{ fontSize: '13.5px', fontWeight: 650, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                          {user?.full_name || 'Candidate'}
                        </div>
                        <div style={{ fontSize: '11px', color: 'var(--text-secondary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', marginTop: '2px' }}>
                          {user?.email || ''}
                        </div>
                      </div>

                      <Link
                        to="/candidate/profile"
                        className="btn btn--ghost btn--block"
                        style={{
                          justifyContent: 'flex-start',
                          padding: '8px 12px',
                          fontSize: '13px',
                          borderRadius: '0px',
                          color: 'var(--text)',
                        }}
                      >
                        Profile Settings
                      </Link>

                      <button
                        type="button"
                        className="btn btn--ghost btn--block"
                        onClick={handleLogout}
                        style={{
                          justifyContent: 'flex-start',
                          padding: '8px 12px',
                          fontSize: '13px',
                          borderRadius: '0px',
                          color: 'var(--danger)',
                        }}
                      >
                        Sign Out
                      </button>
                    </div>
                  </>
                )}
              </div>
            </div>
          </div>
        </header>

        {/* Scrollable child viewport content */}
        <main style={{ flex: 1, overflowY: 'auto' }}>
          {profile && (!profile.email_verified || !profile.phone_verified) && (
            <div className="banner banner--warning" style={{ margin: 'var(--space-4) var(--space-6) 0', borderRadius: 'var(--radius-cards)', padding: '12px 16px', fontSize: 'var(--text-sm)', border: '1px solid var(--warning)', background: 'var(--warning-bg)', color: 'var(--text)' }}>
              ⚠️ <strong>Verification Required:</strong> You must verify your email and phone number to upload resumes, apply to jobs, or schedule interviews. <Link to="/candidate/profile" style={{ textDecoration: 'underline', fontWeight: 600 }}>Go to Profile Settings</Link> to complete verification.
            </div>
          )}
          <AnimatePresence mode="wait">
            <AnimatedPage key={pathname}>{children}</AnimatedPage>
          </AnimatePresence>
        </main>
      </div>

      {/* Embedded CSS for responsive behaviors */}
      <style>{`
        @media (min-width: 901px) {
          .candidate-hamburger {
            display: none !important;
          }
        }
        @media (max-width: 900px) {
          .candidate-sidebar-desktop {
            display: none !important;
          }
        }
      `}</style>
    </div>
  )
}
