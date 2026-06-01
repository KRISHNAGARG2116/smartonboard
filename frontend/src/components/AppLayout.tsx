import { useState, useEffect, type ReactNode } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useTheme } from '../context/ThemeContext'
import { api, fetchJobs, fetchApplications } from '../api'

interface AppLayoutProps {
  children: ReactNode
}

interface ActivityEvent {
  id: string
  title: string
  detail: string
  time: string
  type: 'info' | 'success' | 'warning' | 'danger'
}

export default function AppLayout({ children }: AppLayoutProps) {
  const { pathname } = useLocation()
  const navigate = useNavigate()
  const { user, logout } = useAuth()
  const { theme, toggleTheme } = useTheme()

  // Layout States
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false)
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false)
  const [isActivityDrawerOpen, setIsActivityDrawerOpen] = useState(false)
  const [isCommandPaletteOpen, setIsCommandPaletteOpen] = useState(false)
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false)
  const [isTenantMenuOpen, setIsTenantMenuOpen] = useState(false)

  // Remote searchable data states
  const [jobs, setJobs] = useState<any[]>([])
  const [applications, setApplications] = useState<any[]>([])
  const [employees, setEmployees] = useState<any[]>([])

  // Tenant / Workspace switching state
  const tenants = [
    { id: 'us-west', name: 'Cyberdyne Systems Corp (US-West)', active: true },
    { id: 'eu-central', name: 'Cyberdyne Systems Corp (EU-Central)', active: false },
    { id: 'apac', name: 'Cyberdyne Systems Corp (APAC)', active: false },
  ]
  const [activeTenant, setActiveTenant] = useState(tenants[0])

  // Command palette search state & item listing
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedIndex, setSelectedIndex] = useState(0)

  // Formulated live operational activity stream events
  const [activityEvents, setActivityEvents] = useState<ActivityEvent[]>([
    {
      id: 'evt-1',
      title: 'Candidate converted to Employee',
      detail: 'Sarah Connor converted to Software Engineer (Full-Time)',
      time: '2 mins ago',
      type: 'success',
    },
    {
      id: 'evt-2',
      title: 'Escalation triggered',
      detail: 'Level 2 Escalation: Overdue onboarding document checklist (I-9 form verification)',
      time: '15 mins ago',
      type: 'danger',
    },
    {
      id: 'evt-3',
      title: 'HRIS sync completed',
      detail: 'HiBob HRIS adapter synchronized 4 new employee records successfully',
      time: '1 hour ago',
      type: 'success',
    },
    {
      id: 'evt-4',
      title: 'Interview scheduled',
      detail: 'Hiring Panel for Julie Vance (Security Operations) scheduled for tomorrow',
      time: '2 hours ago',
      type: 'info',
    },
    {
      id: 'evt-5',
      title: 'NDA signed',
      detail: 'Pre-boarding candidate cryptographic NDA signature verified matching identity',
      time: '4 hours ago',
      type: 'success',
    },
    {
      id: 'evt-6',
      title: 'Committee decision submitted',
      detail: 'Voter choice "STRONG HIRE" filed for John Connor by Sarah Connor (committee chair)',
      time: '5 hours ago',
      type: 'info',
    },
    {
      id: 'evt-7',
      title: 'Sync failure detected',
      detail: 'Failed sweeping Gusto Outbox: Invalid OAuth Token connection parameter',
      time: '1 day ago',
      type: 'danger',
    },
    {
      id: 'evt-8',
      title: 'Escalation resolved',
      detail: 'Level 1 escalation resolved by hiring manager for IT laptop kit confirmation',
      time: '1 day ago',
      type: 'warning',
    },
  ])

  // Fetch jobs, applications, and employees on mount or user log
  useEffect(() => {
    if (user) {
      fetchJobs().then(setJobs).catch(() => {})
      fetchApplications().then(setApplications).catch(() => {})
      api
        .get('/v1/employees')
        .then((r) => setEmployees(r.data))
        .catch(() => {})
    }
  }, [user])

  // Keypress listener for Command Palette (Ctrl+K / Cmd+K)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        setIsCommandPaletteOpen((prev) => !prev)
      }
      if (e.key === 'Escape') {
        setIsCommandPaletteOpen(false)
        setIsActivityDrawerOpen(false)
        setIsUserMenuOpen(false)
        setIsTenantMenuOpen(false)
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [])

  // Dynamic Event addition simulation to demonstrate system is alive
  const simulateLiveEvent = (title: string, detail: string, type: 'info' | 'success' | 'warning' | 'danger') => {
    const freshEvent: ActivityEvent = {
      id: `evt-${Date.now()}`,
      title,
      detail,
      time: 'Just now',
      type,
    }
    setActivityEvents((prev) => [freshEvent, ...prev])
  }

  // Set up command list containing static actions, dynamic navigation, jobs, candidates, employees
  const staticCommands = [
    {
      name: 'Go to Pipelines Board',
      shortcut: 'G P',
      category: 'Navigation',
      action: () => navigate('/dashboard'),
    },
    {
      name: 'Go to Landing Gateway',
      shortcut: 'G L',
      category: 'Navigation',
      action: () => navigate('/'),
    },
    {
      name: 'Go to HRIS Sync Logs',
      shortcut: 'G S',
      category: 'Navigation',
      action: () => navigate('/results'),
    },
    {
      name: 'Go to Candidate pre-boarding Portal',
      shortcut: 'G C',
      category: 'Navigation',
      action: () => navigate('/candidate'),
    },
    {
      name: 'Toggle Purple Dream (Dark) / Ocean Blue (Light)',
      shortcut: 'T T',
      category: 'Actions',
      action: toggleTheme,
    },
    {
      name: 'Simulate Sync HRIS Outbox',
      shortcut: 'S O',
      category: 'Operations',
      action: () => {
        simulateLiveEvent(
          'HRIS outbox sweep triggered',
          'Recruiter manually requested transactional outbox sweep. Processing 1 pending queue record.',
          'info'
        )
        alert('Outbox sync queued! Dynamic event posted in activity stream.')
      },
    },
    {
      name: 'Create Job Opening',
      shortcut: 'C J',
      category: 'Actions',
      action: () => {
        navigate('/dashboard')
        alert('Scroll down to "New run" form on the sidebar to declare your Job Opening.')
      },
    },
    {
      name: 'Log Out of Workspace',
      shortcut: 'L O',
      category: 'System',
      action: () => {
        logout()
        navigate('/login')
      },
    },
  ]

  // Filter candidates from applications list
  const candidatesFromApps = applications
    .map((app) => app.candidate)
    .filter(Boolean)
    .map((cand) => ({
      name: `Open Record: ${cand.full_name}`,
      subtitle: `Candidate · ${cand.email}`,
      category: 'Candidates',
      shortcut: undefined as string | undefined,
      action: () => {
        navigate('/dashboard')
        alert(`Accessing candidate details: ${cand.full_name}`)
      },
    }))

  // Filter jobs
  const jobsSearch = jobs.map((job) => ({
    name: `View Job: ${job.title}`,
    subtitle: `Job · ${job.department}`,
    category: 'Jobs',
    shortcut: undefined as string | undefined,
    action: () => {
      navigate('/dashboard')
      alert(`Job Selected: ${job.title}`)
    },
  }))

  // Filter employees
  const employeesSearch = employees.map((emp) => ({
    name: `Open Profile: ${emp.full_name}`,
    subtitle: `Employee · ${emp.department} · ${emp.status}`,
    category: 'Employees',
    shortcut: undefined as string | undefined,
    action: () => {
      navigate('/dashboard')
      alert(`Opening employee dashboard for: ${emp.full_name}`)
    },
  }))

  // Combined command items matching search query
  const allSearchableItems = [
    ...staticCommands.map((c) => ({ name: c.name, subtitle: c.category, category: c.category, shortcut: c.shortcut, action: c.action })),
    ...candidatesFromApps,
    ...jobsSearch,
    ...employeesSearch,
  ]

  const filteredItems = allSearchableItems.filter(
    (item) =>
      item.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.category.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (item.subtitle && item.subtitle.toLowerCase().includes(searchQuery.toLowerCase()))
  )

  // Reset index when search changes
  useEffect(() => {
    setSelectedIndex(0)
  }, [searchQuery])

  // Handle Command selection
  const handleSelectCommand = (item: typeof allSearchableItems[0]) => {
    item.action()
    setIsCommandPaletteOpen(false)
    setSearchQuery('')
  }

  // Keyboard navigation inside Palette
  const handlePaletteKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setSelectedIndex((prev) => (prev + 1) % filteredItems.length)
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setSelectedIndex((prev) => (prev - 1 + filteredItems.length) % filteredItems.length)
    } else if (e.key === 'Enter') {
      e.preventDefault()
      if (filteredItems[selectedIndex]) {
        handleSelectCommand(filteredItems[selectedIndex])
      }
    }
  }

  const unreadCount = activityEvents.length

  return (
    <div
      className="app-shell"
      style={{
        display: 'flex',
        flexDirection: 'row',
        minHeight: '100vh',
        background: 'var(--bg)',
        color: 'var(--text)',
        transition: 'background var(--duration-normal), color var(--duration-normal)',
      }}
    >
      {/* 1. Left Collapsible Sidebar */}
      <aside
        className={`sidebar ${isSidebarCollapsed ? 'sidebar--collapsed' : ''} ${
          isMobileMenuOpen ? 'sidebar--mobile-open' : ''
        }`}
        style={{
          width: isSidebarCollapsed ? '68px' : '260px',
          background: 'var(--sidebar)',
          borderRight: '1px solid var(--border)',
          display: 'flex',
          flexDirection: 'column',
          transition: 'width 240ms cubic-bezier(0.16, 1, 0.3, 1), background var(--duration-normal)',
          zIndex: 150,
          position: 'relative',
        }}
      >
        {/* Sidebar Header: Workspace / Tenant Switcher */}
        <div
          style={{
            height: 'var(--header-h)',
            display: 'flex',
            alignItems: 'center',
            padding: '0 var(--space-4)',
            borderBottom: '1px solid var(--border)',
            gap: 'var(--space-2)',
            position: 'relative',
            cursor: 'pointer',
          }}
          onClick={() => !isSidebarCollapsed && setIsTenantMenuOpen(!isTenantMenuOpen)}
        >
          {/* Logo Hexagon Mark */}
          <div
            style={{
              width: '32px',
              height: '32px',
              minWidth: '32px',
              borderRadius: '10px',
              background: 'linear-gradient(135deg, var(--accent) 0%, var(--accent-hover) 100%)',
              display: 'grid',
              placeItems: 'center',
              color: 'var(--text-inverse)',
              fontWeight: 800,
              fontSize: '14px',
              boxShadow: '0 2px 8px rgba(37, 99, 235, 0.25)',
            }}
          >
            SO
          </div>

          {!isSidebarCollapsed && (
            <div style={{ display: 'flex', flexDirection: 'column', flex: 1, overflow: 'hidden', marginLeft: '6px' }}>
              <span
                style={{
                  fontSize: '9px',
                  fontWeight: 700,
                  textTransform: 'uppercase',
                  color: 'var(--text-tertiary)',
                  letterSpacing: '0.08em',
                }}
              >
                Tenant Account
              </span>
              <span
                style={{
                  fontSize: '13px',
                  fontWeight: 600,
                  whiteSpace: 'nowrap',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                }}
              >
                {activeTenant.name.split(' (')[0]}
              </span>
            </div>
          )}

          {!isSidebarCollapsed && (
            <span style={{ fontSize: '10px', color: 'var(--text-tertiary)', marginLeft: 'auto' }}>
              ▼
            </span>
          )}

          {/* Tenant Switching Dropdown Menu */}
          {isTenantMenuOpen && !isSidebarCollapsed && (
            <div
              className="card"
              style={{
                position: 'absolute',
                top: '52px',
                left: '16px',
                right: '16px',
                zIndex: 220,
                boxShadow: 'var(--shadow-lg)',
                background: 'var(--surface)',
                borderRadius: '12px',
                padding: 'var(--space-2)',
                border: '1px solid var(--border)',
              }}
              onClick={(e) => e.stopPropagation()}
            >
              <div
                style={{
                  padding: 'var(--space-2) var(--space-3)',
                  fontSize: '10px',
                  fontWeight: 700,
                  color: 'var(--text-tertiary)',
                  textTransform: 'uppercase',
                  borderBottom: '1px solid var(--border)',
                  marginBottom: 'var(--space-1)',
                }}
              >
                Switch Workspace
              </div>
              {tenants.map((ten) => (
                <button
                  key={ten.id}
                  type="button"
                  className="btn btn--ghost btn--block"
                  style={{
                    justifyContent: 'flex-start',
                    padding: '8px var(--space-3)',
                    fontSize: '13px',
                    fontWeight: ten.id === activeTenant.id ? 700 : 500,
                    color: ten.id === activeTenant.id ? 'var(--accent)' : 'var(--text)',
                    background: ten.id === activeTenant.id ? 'var(--accent-subtle)' : 'transparent',
                    borderRadius: '8px',
                  }}
                  onClick={() => {
                    setActiveTenant(ten)
                    setIsTenantMenuOpen(false)
                    simulateLiveEvent(
                      'Tenant Workspace Switched',
                      `Successfully connected to workspace ${ten.name}`,
                      'info'
                    )
                  }}
                >
                  <span style={{ marginRight: '6px' }}>🏢</span>
                  {ten.name.replace('Cyberdyne Systems Corp ', '')}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Sidebar Nav links */}
        <nav
          style={{
            flex: 1,
            padding: 'var(--space-4) var(--space-2)',
            display: 'flex',
            flexDirection: 'column',
            gap: '6px',
            overflowY: 'auto',
          }}
          aria-label="Sidebar Workspace"
        >
          {/* Navigation Links */}
          <Link
            to="/"
            className={`btn btn--ghost btn--block ${pathname === '/' ? 'nav-link--active' : ''}`}
            style={{
              justifyContent: 'flex-start',
              padding: '10px 14px',
              borderRadius: '10px',
              fontSize: '13.5px',
              fontWeight: 550,
            }}
          >
            <span style={{ display: 'grid', placeItems: 'center', minWidth: '20px', marginRight: '6px' }}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
                <polyline points="9 22 9 12 15 12 15 22" />
              </svg>
            </span>
            {!isSidebarCollapsed && <span>Landing Gateway</span>}
          </Link>

          <Link
            to="/dashboard"
            className={`btn btn--ghost btn--block ${pathname === '/dashboard' ? 'nav-link--active' : ''}`}
            style={{
              justifyContent: 'flex-start',
              padding: '10px 14px',
              borderRadius: '10px',
              fontSize: '13.5px',
              fontWeight: 550,
            }}
          >
            <span style={{ display: 'grid', placeItems: 'center', minWidth: '20px', marginRight: '6px' }}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <rect width="18" height="18" x="3" y="3" rx="2" ry="2" />
                <line x1="9" x2="9" y1="3" y2="21" />
                <line x1="15" x2="15" y1="3" y2="21" />
              </svg>
            </span>
            {!isSidebarCollapsed && <span>Pipelines Board</span>}
          </Link>

          <Link
            to="/results"
            className={`btn btn--ghost btn--block ${pathname === '/results' ? 'nav-link--active' : ''}`}
            style={{
              justifyContent: 'flex-start',
              padding: '10px 14px',
              borderRadius: '10px',
              fontSize: '13.5px',
              fontWeight: 550,
            }}
          >
            <span style={{ display: 'grid', placeItems: 'center', minWidth: '20px', marginRight: '6px' }}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 2v20" />
                <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
              </svg>
            </span>
            {!isSidebarCollapsed && <span>HRIS sync logs</span>}
          </Link>

          <Link
            to="/candidate"
            className={`btn btn--ghost btn--block ${pathname === '/candidate' ? 'nav-link--active' : ''}`}
            style={{
              justifyContent: 'flex-start',
              padding: '10px 14px',
              borderRadius: '10px',
              fontSize: '13.5px',
              fontWeight: 550,
            }}
          >
            <span style={{ display: 'grid', placeItems: 'center', minWidth: '20px', marginRight: '6px' }}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
                <circle cx="9" cy="7" r="4" />
                <path d="M22 21v-2a4 4 0 0 0-3-3.87" />
                <path d="M16 3.13a4 4 0 0 1 0 7.75" />
              </svg>
            </span>
            {!isSidebarCollapsed && <span>Candidate Portal</span>}
          </Link>

          {/* Section Divider */}
          {!isSidebarCollapsed && (
            <div
              style={{
                padding: 'var(--space-4) var(--space-4) var(--space-2)',
                fontSize: '10px',
                fontWeight: 700,
                color: 'var(--text-tertiary)',
                textTransform: 'uppercase',
                letterSpacing: '0.08em',
              }}
            >
              Control Center
            </div>
          )}

          <div
            className="btn btn--ghost btn--block"
            onClick={() => {
              navigate('/dashboard')
              alert('Redirecting to dashboard system settings context...')
            }}
            style={{
              justifyContent: 'flex-start',
              padding: '10px 14px',
              borderRadius: '10px',
              fontSize: '13.5px',
              fontWeight: 550,
              cursor: 'pointer',
            }}
          >
            <span style={{ display: 'grid', placeItems: 'center', minWidth: '20px', marginRight: '6px' }}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="3" />
                <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
              </svg>
            </span>
            {!isSidebarCollapsed && <span>System Settings</span>}
          </div>

          <div
            className="btn btn--ghost btn--block"
            onClick={() => setIsActivityDrawerOpen(true)}
            style={{
              justifyContent: 'flex-start',
              padding: '10px 14px',
              borderRadius: '10px',
              fontSize: '13.5px',
              fontWeight: 550,
              cursor: 'pointer',
            }}
          >
            <span style={{ display: 'grid', placeItems: 'center', minWidth: '20px', marginRight: '6px' }}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9" />
                <path d="M10.3 21a1.94 1.94 0 0 0 3.4 0" />
              </svg>
            </span>
            {!isSidebarCollapsed && (
              <div style={{ display: 'flex', justifyContent: 'space-between', width: '100%', alignItems: 'center' }}>
                <span>Activity stream</span>
                <span
                  style={{
                    fontSize: '10px',
                    fontWeight: 700,
                    padding: '2px 8px',
                    borderRadius: '8px',
                    background: 'var(--accent)',
                    color: 'var(--text-inverse)',
                  }}
                >
                  {unreadCount}
                </span>
              </div>
            )}
          </div>
        </nav>

        {/* Sidebar Footer Collapse Arrow Toggle */}
        <div
          style={{
            padding: 'var(--space-4)',
            borderTop: '1px solid var(--border)',
            display: 'flex',
            justifyContent: isSidebarCollapsed ? 'center' : 'flex-end',
            background: 'var(--bg-subtle)',
          }}
        >
          <button
            type="button"
            className="icon-btn"
            style={{
              width: '36px',
              height: '36px',
              borderRadius: '50%',
              background: 'var(--surface)',
              border: '1px solid var(--border)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: 'var(--shadow-sm)',
            }}
            onClick={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
            aria-label={isSidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
              style={{
                transform: isSidebarCollapsed ? 'rotate(180deg)' : 'none',
                transition: 'transform 200ms ease',
              }}
            >
              <line x1="19" y1="12" x2="5" y2="12" />
              <polyline points="12 19 5 12 12 5" />
            </svg>
          </button>
        </div>
      </aside>

      {/* 2. Main Page Context Shell Container */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0, minHeight: '100vh' }}>
        
        {/* Global sticky Top Header Navigation */}
        <header
          className="app-header"
          style={{
            position: 'sticky',
            top: 0,
            zIndex: 100,
            height: 'var(--header-h)',
            background: 'var(--surface)',
            borderBottom: '1px solid var(--border)',
            backdropFilter: 'blur(12px)',
            transition: 'background var(--duration-normal), border-color var(--duration-normal)',
          }}
        >
          <div
            className="header-inner"
            style={{
              paddingInline: 'var(--space-6)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              height: '100%',
              maxWidth: '100%',
            }}
          >
            {/* Header Left Trigger Button & Search Activation */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)', flex: 1 }}>
              <button
                type="button"
                className="icon-btn mobile-menu-btn"
                style={{
                  width: '38px',
                  height: '38px',
                  borderRadius: '10px',
                  background: 'var(--bg-subtle)',
                  border: '1px solid var(--border)',
                }}
                onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
                aria-label="Toggle mobile menu"
              >
                ☰
              </button>

              {/* Command Palette search Trigger Bar */}
              <button
                type="button"
                onClick={() => setIsCommandPaletteOpen(true)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 'var(--space-3)',
                  padding: '9px 14px',
                  borderRadius: '10px',
                  border: '1px solid var(--border)',
                  background: 'var(--bg-subtle)',
                  color: 'var(--text-secondary)',
                  fontSize: '13px',
                  cursor: 'pointer',
                  width: 'min(380px, 100%)',
                  textAlign: 'left',
                  boxShadow: 'var(--shadow-sm)',
                  fontWeight: 500,
                }}
              >
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" style={{ color: 'var(--text-tertiary)' }}>
                  <circle cx="11" cy="11" r="8" />
                  <line x1="21" y1="21" x2="16.65" y2="16.65" />
                </svg>
                <span>Search candidates, actions...</span>
                <kbd
                  style={{
                    marginLeft: 'auto',
                    background: 'var(--surface)',
                    border: '1px solid var(--border)',
                    padding: '2px 6px',
                    borderRadius: '6px',
                    fontSize: '10px',
                    fontFamily: 'var(--font-mono)',
                    color: 'var(--text-tertiary)',
                  }}
                >
                  Ctrl+K
                </kbd>
              </button>
            </div>

            {/* Header Right Tools: Theme Toggle, Bell, User Dropdown */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
              
              {/* Premium Light/Dark Switcher */}
              <button
                type="button"
                className="icon-btn"
                onClick={toggleTheme}
                title={theme === 'dark' ? 'Ocean Blue Light Theme' : 'Purple Dream Dark Theme'}
                style={{
                  width: '38px',
                  height: '38px',
                  borderRadius: '50%',
                  background: 'var(--bg-subtle)',
                  border: '1px solid var(--border)',
                  display: 'grid',
                  placeItems: 'center',
                  cursor: 'pointer',
                }}
              >
                {theme === 'dark' ? (
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
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
                ) : (
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
                  </svg>
                )}
              </button>

              {/* Dynamic Notification Bell Indicator */}
              <button
                type="button"
                className="icon-btn"
                onClick={() => setIsActivityDrawerOpen(true)}
                title="Open Activity Drawer"
                style={{
                  width: '38px',
                  height: '38px',
                  position: 'relative',
                  borderRadius: '50%',
                  background: 'var(--bg-subtle)',
                  border: '1px solid var(--border)',
                  display: 'grid',
                  placeItems: 'center',
                  cursor: 'pointer',
                }}
              >
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
                  <path d="M13.73 21a2 2 0 0 1-3.46 0" />
                </svg>
                <span
                  style={{
                    position: 'absolute',
                    top: '2px',
                    right: '2px',
                    width: '9px',
                    height: '9px',
                    background: 'var(--danger)',
                    borderRadius: '50%',
                    border: '1.5px solid var(--surface)',
                    boxShadow: '0 0 0 1.5px var(--danger)',
                  }}
                />
              </button>

              {/* User Recruiter dropdown list menu */}
              {user ? (
                <div style={{ position: 'relative' }}>
                  <button
                    type="button"
                    onClick={() => setIsUserMenuOpen(!isUserMenuOpen)}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 'var(--space-2)',
                      padding: '4px 14px 4px 4px',
                      borderRadius: '999px',
                      border: '1px solid var(--border)',
                      background: 'var(--surface)',
                      cursor: 'pointer',
                      boxShadow: 'var(--shadow-sm)',
                    }}
                  >
                    <div
                      style={{
                        width: '30px',
                        height: '30px',
                        borderRadius: '50%',
                        background: 'var(--accent)',
                        display: 'grid',
                        placeItems: 'center',
                        color: 'var(--text-inverse)',
                        fontWeight: 'bold',
                        fontSize: '13px',
                      }}
                    >
                      {user.full_name ? user.full_name[0] : 'U'}
                    </div>
                    <span style={{ fontSize: '13.5px', fontWeight: 600, color: 'var(--text)' }}>
                      {user.full_name}
                    </span>
                    <span style={{ fontSize: '9px', color: 'var(--text-tertiary)' }}>▼</span>
                  </button>

                  {isUserMenuOpen && (
                    <div
                      className="card"
                      style={{
                        position: 'absolute',
                        top: '44px',
                        right: 0,
                        width: '220px',
                        zIndex: 180,
                        boxShadow: 'var(--shadow-lg)',
                        background: 'var(--surface)',
                        borderRadius: '14px',
                        padding: 'var(--space-2)',
                        border: '1px solid var(--border)',
                      }}
                    >
                      <div
                        style={{
                          padding: 'var(--space-2) var(--space-3)',
                          borderBottom: '1px solid var(--border)',
                          display: 'flex',
                          flexDirection: 'column',
                          marginBottom: 'var(--space-1)',
                        }}
                      >
                        <span style={{ fontSize: '13px', fontWeight: 700 }}>{user.full_name}</span>
                        <span style={{ fontSize: '11px', color: 'var(--text-tertiary)', wordBreak: 'break-all' }}>
                          {user.email}
                        </span>
                      </div>

                      <button
                        type="button"
                        className="btn btn--ghost btn--block"
                        onClick={toggleTheme}
                        style={{
                          justifyContent: 'flex-start',
                          fontSize: '13px',
                          padding: '8px var(--space-3)',
                          borderRadius: '8px',
                        }}
                      >
                        Theme: {theme === 'dark' ? 'Purple Dream' : 'Ocean Blue'}
                      </button>

                      <button
                        type="button"
                        className="btn btn--ghost btn--block"
                        onClick={() => {
                          logout()
                          navigate('/login')
                          setIsUserMenuOpen(false)
                        }}
                        style={{
                          justifyContent: 'flex-start',
                          color: 'var(--danger)',
                          fontSize: '13px',
                          padding: '8px var(--space-3)',
                          borderRadius: '8px',
                        }}
                      >
                        Sign out
                      </button>
                    </div>
                  )}
                </div>
              ) : (
                <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
                  <Link to="/login" className="btn btn--ghost btn--sm" style={{ borderRadius: '10px' }}>
                    Sign in
                  </Link>
                  <Link to="/register" className="btn btn--primary btn--sm" style={{ borderRadius: '10px' }}>
                    Get started
                  </Link>
                </div>
              )}
            </div>
          </div>
        </header>

        {/* 3. Main Workspace Viewport children */}
        <main
          className="app-main"
          id="main-content"
          style={{
            flex: 1,
            padding: 'var(--space-6)',
            overflowY: 'auto',
            background: 'var(--bg)',
            transition: 'background var(--duration-normal)',
          }}
        >
          {children}
        </main>
      </div>

      {/* 4. Slide-Out Global Activity Feed Drawer (bell drawer) */}
      {isActivityDrawerOpen && (
        <>
          <div
            className="drawer-backdrop"
            style={{ zIndex: 200 }}
            onClick={() => setIsActivityDrawerOpen(false)}
          />
          <aside
            className="drawer"
            style={{
              display: 'flex',
              flexDirection: 'column',
              width: 'min(460px, 100vw)',
              borderRadius: '20px 0 0 20px',
              borderLeft: '1px solid var(--border)',
              background: 'var(--surface)',
              zIndex: 201,
            }}
          >
            <div
              className="drawer-header"
              style={{
                padding: 'var(--space-6)',
                borderBottom: '1px solid var(--border)',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
              }}
            >
              <div>
                <h2 style={{ fontSize: 'var(--text-lg)', fontWeight: 700, letterSpacing: '-0.01em' }}>
                  Global Activity Stream
                </h2>
                <p style={{ fontSize: 'var(--text-xs)', color: 'var(--text-tertiary)', marginTop: '2px' }}>
                  Real-time hiring & synchronization logs
                </p>
              </div>
              <button
                type="button"
                className="icon-btn"
                style={{
                  border: '1px solid var(--border)',
                  borderRadius: '50%',
                  width: '32px',
                  height: '32px',
                  display: 'grid',
                  placeItems: 'center',
                }}
                onClick={() => setIsActivityDrawerOpen(false)}
              >
                ✕
              </button>
            </div>

            <div
              className="drawer-body"
              style={{
                flex: 1,
                overflowY: 'auto',
                padding: 'var(--space-6)',
                display: 'flex',
                flexDirection: 'column',
                gap: 'var(--space-4)',
              }}
            >
              {activityEvents.length > 0 ? (
                activityEvents.map((event) => (
                  <article
                    key={event.id}
                    style={{
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '6px',
                      padding: 'var(--space-4)',
                      borderRadius: '16px',
                      border: '1px solid var(--border)',
                      background: 'var(--bg-subtle)',
                      transition: 'transform var(--duration-fast)',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span
                        className={`badge badge--${
                          event.type === 'danger'
                            ? 'reject'
                            : event.type === 'warning'
                            ? 'interview'
                            : event.type === 'success'
                            ? 'hire'
                            : 'neutral'
                        }`}
                        style={{ fontSize: '9px', fontWeight: 700 }}
                      >
                        {event.type === 'danger'
                          ? 'Failed'
                          : event.type === 'warning'
                          ? 'Escalation'
                          : event.type === 'success'
                          ? 'Completed'
                          : 'Operational'}
                      </span>
                      <span style={{ fontSize: '11px', color: 'var(--text-tertiary)' }}>{event.time}</span>
                    </div>

                    <h3 style={{ fontSize: '13.5px', fontWeight: 700, color: 'var(--text)', margin: 0 }}>
                      {event.title}
                    </h3>
                    <p
                      style={{
                        fontSize: '12.5px',
                        color: 'var(--text-secondary)',
                        margin: 0,
                        lineHeight: '1.4',
                      }}
                    >
                      {event.detail}
                    </p>
                  </article>
                ))
              ) : (
                <div style={{ textAlign: 'center', padding: 'var(--space-12) 0', color: 'var(--text-tertiary)' }}>
                  No historical event logs in cache.
                </div>
              )}
            </div>

            <div
              style={{
                padding: 'var(--space-4)',
                borderTop: '1px solid var(--border)',
                background: 'var(--bg-subtle)',
                textAlign: 'center',
                display: 'flex',
                gap: '12px',
              }}
            >
              <button
                type="button"
                className="btn btn--secondary btn--sm btn--block"
                onClick={() => {
                  simulateLiveEvent(
                    'Simulated Dynamic Sync',
                    'Recruiter manually sweepedoutbox queues successfully.',
                    'success'
                  )
                }}
              >
                Simulate Sweeping
              </button>
              <button
                type="button"
                className="btn btn--secondary btn--sm btn--block"
                style={{ color: 'var(--danger)' }}
                onClick={() => setActivityEvents([])}
              >
                Clear all activities
              </button>
            </div>
          </aside>
        </>
      )}

      {/* 5. Frosted Command Palette Overlay (Ctrl+K) */}
      {isCommandPaletteOpen && (
        <>
          <div
            className="drawer-backdrop"
            style={{ background: 'rgba(10, 10, 18, 0.4)', backdropFilter: 'blur(8px)', zIndex: 300 }}
            onClick={() => setIsCommandPaletteOpen(false)}
          />
          <div
            style={{
              position: 'fixed',
              top: '12%',
              left: '50%',
              transform: 'translateX(-50%)',
              width: 'min(640px, 92vw)',
              zIndex: 301,
              animation: 'fade-in 140ms ease-out',
            }}
          >
            <div
              className="card"
              style={{
                padding: 0,
                overflow: 'hidden',
                boxShadow: 'var(--shadow-lg)',
                borderRadius: '20px',
                border: '1px solid var(--border)',
                background: 'var(--surface)',
              }}
              onKeyDown={handlePaletteKeyDown}
            >
              {/* Command Palette search bar input */}
              <div
                style={{
                  borderBottom: '1px solid var(--border)',
                  padding: 'var(--space-4)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 'var(--space-3)',
                }}
              >
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--text-secondary)" strokeWidth="2.5">
                  <circle cx="11" cy="11" r="8" />
                  <line x1="21" y1="21" x2="16.65" y2="16.65" />
                </svg>
                <input
                  type="text"
                  placeholder="Search candidates, workspace actions, jobs, employees..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  style={{
                    border: 'none',
                    background: 'none',
                    color: 'var(--text)',
                    fontSize: '15px',
                    width: '100%',
                    outline: 'none',
                    fontWeight: 500,
                  }}
                  autoFocus
                />
                <button
                  type="button"
                  className="btn btn--secondary btn--sm"
                  style={{ borderRadius: '8px', padding: '4px 10px', fontSize: '11px', fontWeight: 700 }}
                  onClick={() => setIsCommandPaletteOpen(false)}
                >
                  ESC
                </button>
              </div>

              {/* Command Palette list matchings */}
              <div
                style={{
                  maxHeight: '380px',
                  overflowY: 'auto',
                  padding: 'var(--space-2)',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '2px',
                }}
              >
                {filteredItems.length > 0 ? (
                  <div>
                    {/* Render Category Groupings */}
                    {['Navigation', 'Actions', 'Operations', 'Candidates', 'Jobs', 'Employees', 'System'].map(
                      (cat) => {
                        const catCommands = filteredItems.filter((c) => c.category === cat)
                        if (catCommands.length === 0) return null

                        return (
                          <div key={cat} style={{ marginBottom: '8px' }}>
                            <div
                              style={{
                                padding: 'var(--space-2) var(--space-3) 4px',
                                fontSize: '10px',
                                fontWeight: 700,
                                color: 'var(--text-tertiary)',
                                textTransform: 'uppercase',
                                letterSpacing: '0.08em',
                              }}
                            >
                              {cat}
                            </div>
                            {catCommands.map((command) => {
                              // Compute actual index in the global filteredItems array
                              const globalIndex = filteredItems.findIndex((x) => x.name === command.name)
                              const isSelected = globalIndex === selectedIndex

                              return (
                                <button
                                  key={command.name}
                                  type="button"
                                  className="btn btn--ghost btn--block"
                                  onClick={() => handleSelectCommand(command)}
                                  onMouseEnter={() => setSelectedIndex(globalIndex)}
                                  style={{
                                    justifyContent: 'flex-start',
                                    fontSize: '13.5px',
                                    padding: '10px var(--space-4)',
                                    borderRadius: '10px',
                                    textAlign: 'left',
                                    color: isSelected ? 'var(--accent)' : 'var(--text)',
                                    background: isSelected ? 'var(--accent-subtle)' : 'transparent',
                                    transition: 'background 120ms, color 120ms',
                                    border: 'none',
                                    cursor: 'pointer',
                                  }}
                                >
                                  <div style={{ display: 'flex', flexDirection: 'column', flex: 1 }}>
                                    <span style={{ fontWeight: 600 }}>{command.name}</span>
                                    {command.subtitle && command.subtitle !== command.category && (
                                      <span
                                        style={{
                                          fontSize: '11px',
                                          color: isSelected ? 'var(--accent)' : 'var(--text-tertiary)',
                                          opacity: 0.85,
                                          marginTop: '2px',
                                        }}
                                      >
                                        {command.subtitle}
                                      </span>
                                    )}
                                  </div>
                                  {command.shortcut && (
                                    <kbd
                                      style={{
                                        background: isSelected ? 'var(--surface)' : 'var(--bg-subtle)',
                                        border: '1px solid var(--border)',
                                        padding: '2px 6px',
                                        borderRadius: '4px',
                                        fontSize: '9.5px',
                                        fontFamily: 'var(--font-mono)',
                                        color: 'var(--text-tertiary)',
                                      }}
                                    >
                                      {command.shortcut}
                                    </kbd>
                                  )}
                                </button>
                              )
                            })}
                          </div>
                        )
                      }
                    )}
                  </div>
                ) : (
                  <div
                    style={{
                      padding: 'var(--space-12) var(--space-4)',
                      textAlign: 'center',
                      color: 'var(--text-tertiary)',
                      fontSize: '13.5px',
                    }}
                  >
                    No matching records or actions found. Try typing "theme" or "sync".
                  </div>
                )}
              </div>

              {/* Command Palette keyboard hints footer */}
              <div
                style={{
                  borderTop: '1px solid var(--border)',
                  padding: 'var(--space-3) var(--space-4)',
                  background: 'var(--bg-subtle)',
                  display: 'flex',
                  gap: 'var(--space-4)',
                  fontSize: '11.5px',
                  color: 'var(--text-tertiary)',
                  fontWeight: 550,
                }}
              >
                <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <span style={{ border: '1px solid var(--border)', padding: '0 4px', borderRadius: '3px', background: 'var(--surface)' }}>↑↓</span> navigate
                </span>
                <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <span style={{ border: '1px solid var(--border)', padding: '0 4px', borderRadius: '3px', background: 'var(--surface)' }}>↵</span> enter to select
                </span>
                <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <span style={{ border: '1px solid var(--border)', padding: '0 4px', borderRadius: '3px', background: 'var(--surface)' }}>esc</span> close
                </span>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
