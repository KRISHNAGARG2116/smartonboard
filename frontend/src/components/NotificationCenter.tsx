import type { ActivityEvent } from './AppLayout'

interface NotificationCenterProps {
  isOpen: boolean
  onClose: () => void
  activityEvents: ActivityEvent[]
  onSimulateSweep: () => void
  onClearAll: () => void
}

export default function NotificationCenter({
  isOpen,
  onClose,
  activityEvents,
  onSimulateSweep,
  onClearAll,
}: NotificationCenterProps) {
  if (!isOpen) return null

  return (
    <>
      <div
        className="drawer-backdrop"
        style={{ zIndex: 200 }}
        onClick={onClose}
      />
      <aside
        className="drawer"
        style={{
          display: 'flex',
          flexDirection: 'column',
          width: 'min(460px, 100vw)',
          borderRadius: '0px',
          borderLeft: '1px solid var(--color-cork-shadow)',
          background: 'var(--bg)',
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
            onClick={onClose}
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
                  borderRadius: 'var(--radius-cards)',
                  border: '1px solid var(--border)',
                  background: 'transparent',
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
            onClick={onSimulateSweep}
          >
            Simulate Sweeping
          </button>
          <button
            type="button"
            className="btn btn--secondary btn--sm btn--block"
            style={{ color: 'var(--danger)' }}
            onClick={onClearAll}
          >
            Clear all activities
          </button>
        </div>
      </aside>
    </>
  )
}
