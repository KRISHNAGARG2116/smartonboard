import { useState, useEffect, useRef } from 'react'

interface NotificationItem {
  id: string
  title: string
  message: string
  type: string
  status: 'unread' | 'read'
  created_at: string
}

export default function RecruiterNotificationBell() {
  const [isOpen, setIsOpen] = useState(false)
  const [showPrefs, setShowPrefs] = useState(false)
  const [notifications, setNotifications] = useState<NotificationItem[]>([
    {
      id: 'notif-1',
      title: '📅 Interview Reminder',
      message: 'Interview with Sarah Jenkins starts in 15 minutes.',
      type: 'interview',
      status: 'unread',
      created_at: '15m ago'
    },
    {
      id: 'notif-2',
      title: '🤖 Match Report Ready',
      message: 'AI screening complete for Senior Frontend Engineer role.',
      type: 'ai',
      status: 'unread',
      created_at: '1h ago'
    },
    {
      id: 'notif-3',
      title: '⚙️ Integration Sync Failure',
      message: 'Google Calendar access token expired. Please reconnect.',
      type: 'sla',
      status: 'read',
      created_at: '1d ago'
    }
  ])

  // Preference states
  const [emailEnabled, setEmailEnabled] = useState(true)
  const [inAppEnabled, setInAppEnabled] = useState(true)
  const [digestEnabled, setDigestEnabled] = useState(false)

  const dropdownRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handleOutsideClick = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setIsOpen(false)
      }
    }
    document.addEventListener('mousedown', handleOutsideClick)
    return () => document.removeEventListener('mousedown', handleOutsideClick)
  }, [])

  const unreadCount = notifications.filter(n => n.status === 'unread').length

  const handleMarkAsRead = (id: string) => {
    setNotifications(prev =>
      prev.map(n => (n.id === id ? { ...n, status: 'read' as const } : n))
    )
  }

  const handleBulkMarkAllRead = () => {
    setNotifications(prev => prev.map(n => ({ ...n, status: 'read' as const })))
  }

  return (
    <div ref={dropdownRef} style={{ position: 'relative', display: 'inline-block' }}>
      <button
        type="button"
        onClick={() => {
          setIsOpen(!isOpen)
          setShowPrefs(false)
        }}
        aria-label="View notifications"
        style={{
          background: 'none',
          border: 'none',
          padding: '8px',
          borderRadius: '50%',
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          position: 'relative'
        }}
      >
        <span style={{ fontSize: '20px' }}>🔔</span>
        {unreadCount > 0 && (
          <span
            style={{
              position: 'absolute',
              top: '4px',
              right: '4px',
              background: 'var(--accent, #ef4444)',
              color: '#ffffff',
              fontSize: '10px',
              fontWeight: 700,
              borderRadius: '50%',
              width: '16px',
              height: '16px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              lineHeight: 1
            }}
          >
            {unreadCount}
          </span>
        )}
      </button>

      {isOpen && (
        <div
          style={{
            position: 'absolute',
            right: 0,
            top: '42px',
            width: '360px',
            background: 'var(--surface, #ffffff)',
            border: '1px solid var(--border, #a3a6af)',
            borderRadius: '12px',
            boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)',
            zIndex: 1000,
            overflow: 'hidden'
          }}
        >
          {/* Panel Header */}
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              padding: '12px 16px',
              borderBottom: '1px solid var(--border-subtle, #f3f4f6)',
              background: 'var(--bg-subtle, #f7f7f8)'
            }}
          >
            <h4 style={{ margin: 0, fontSize: '14px', fontWeight: 700 }}>
              {showPrefs ? '⚙️ Notification Settings' : '🔔 Notifications'}
            </h4>
            <div style={{ display: 'flex', gap: '8px' }}>
              {!showPrefs && unreadCount > 0 && (
                <button
                  type="button"
                  onClick={handleBulkMarkAllRead}
                  style={{ fontSize: '11px', color: 'var(--accent)', fontWeight: 600, border: 'none', background: 'none' }}
                >
                  Mark all read
                </button>
              )}
              <button
                type="button"
                onClick={() => setShowPrefs(!showPrefs)}
                style={{ fontSize: '11px', color: 'var(--text-secondary)', fontWeight: 600, border: 'none', background: 'none' }}
              >
                {showPrefs ? 'Back' : 'Settings'}
              </button>
            </div>
          </div>

          {/* Panel Body */}
          <div style={{ maxHeight: '320px', overflowY: 'auto' }}>
            {showPrefs ? (
              // Preference customization view
              <div style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '12px', fontSize: '13px' }}>
                <label style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span>Email Alerts</span>
                  <input
                    type="checkbox"
                    checked={emailEnabled}
                    onChange={e => setEmailEnabled(e.target.checked)}
                  />
                </label>
                <label style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span>In-App Banner Notifications</span>
                  <input
                    type="checkbox"
                    checked={inAppEnabled}
                    onChange={e => setInAppEnabled(e.target.checked)}
                  />
                </label>
                <label style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span>Daily Digest Summary</span>
                  <input
                    type="checkbox"
                    checked={digestEnabled}
                    onChange={e => setDigestEnabled(e.target.checked)}
                  />
                </label>
                <div style={{ fontSize: '11px', color: 'var(--text-secondary)', borderTop: '1px solid var(--border-subtle)', paddingTop: '8px', marginTop: '4px' }}>
                  Preferences automatically synced. Click "Settings" to return.
                </div>
              </div>
            ) : (
              // Notifications list view
              <div>
                {notifications.length > 0 ? (
                  notifications.map(item => (
                    <div
                      key={item.id}
                      onClick={() => handleMarkAsRead(item.id)}
                      style={{
                        padding: '12px 16px',
                        borderBottom: '1px solid var(--border-subtle, #f3f4f6)',
                        background: item.status === 'unread' ? 'var(--bg-subtle, #f7f7f8)' : 'transparent',
                        cursor: 'pointer',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '4px',
                        fontSize: '12.5px',
                        transition: 'background 150ms'
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
                        <span style={{ fontWeight: item.status === 'unread' ? 700 : 500, color: 'var(--text)' }}>
                          {item.title}
                        </span>
                        <span style={{ fontSize: '10px', color: 'var(--text-secondary)' }}>
                          {item.created_at}
                        </span>
                      </div>
                      <p style={{ margin: 0, color: 'var(--text-secondary)', fontSize: '12px', lineHeight: 1.4 }}>
                        {item.message}
                      </p>
                    </div>
                  ))
                ) : (
                  <div style={{ padding: '24px', textAlign: 'center', color: 'var(--text-secondary)', fontSize: '13px' }}>
                    No notifications yet.
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
