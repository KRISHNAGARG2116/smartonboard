import { useState, useEffect } from 'react'
import { useLocation, Link } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'
import AppLayout from '../components/AppLayout'
import { 
  fetchDlqRecords, 
  fetchSyncMetrics, 
  retryDlqRecord,
  type OnboardResult, 
  type OnboardRequest 
} from '../api'

type Tab = 'documents' | 'training' | 'email'
type DlqTab = 'dlq' | 'metrics'

export default function Results() {
  const location = useLocation()
  const [activeTab, setActiveTab] = useState<Tab>('documents')
  const [activeDlqTab, setActiveDlqTab] = useState<DlqTab>('dlq')
  const [dlqRecords, setDlqRecords] = useState<any[]>([])
  const [syncMetrics, setSyncMetrics] = useState<any[]>([])
  const [dlqLoading, setDlqLoading] = useState(false)
  const [dlqError, setDlqError] = useState<string | null>(null)
  const [actionMessage, setActionMessage] = useState<string | null>(null)

  const state = location.state as { result: OnboardResult; request: OnboardRequest } | null

  const loadDlqData = async () => {
    setDlqLoading(true)
    setDlqError(null)
    try {
      const [records, metrics] = await Promise.all([
        fetchDlqRecords(),
        fetchSyncMetrics()
      ])
      setDlqRecords(records)
      setSyncMetrics(metrics)
    } catch (err: any) {
      setDlqError(err.response?.data?.detail || 'Failed to retrieve DLQ and metrics logs.')
    } finally {
      setDlqLoading(false)
    }
  }

  useEffect(() => {
    if (!state) {
      loadDlqData()
    }
  }, [state])

  const handleRetry = async (recordId: string) => {
    setActionMessage(null)
    try {
      await retryDlqRecord(recordId)
      setActionMessage('Sync retry request successfully submitted!')
      await loadDlqData()
    } catch (err: any) {
      setDlqError(err.response?.data?.detail || 'Failed to retry sync outbox event.')
    }
  }

  if (!state) {
    const dlqTabs: { id: DlqTab; label: string }[] = [
      { id: 'dlq', label: 'Dead Letter Queue (Errors)' },
      { id: 'metrics', label: 'Sync Metrics & Trends' },
    ]

    return (
      <AppLayout>
        <div className="container" style={{ padding: 'var(--space-8) 0 var(--space-16)' }}>
          <header className="page-header" style={{ marginBottom: 'var(--space-6)' }}>
            <div>
              <h1 className="page-header__title">HRIS Sync Logs & Outbox DLQ</h1>
              <p className="page-header__meta">
                Inspect failed transfers in the Dead Letter Queue, view system sync counters, and trigger manual retries.
              </p>
            </div>
            <Link to="/dashboard" className="btn btn--secondary">
              Back to Dashboard
            </Link>
          </header>

          {dlqError && (
            <div className="banner banner--danger" style={{ marginBottom: 'var(--space-4)', borderRadius: '8px' }}>
              ❌ {dlqError}
            </div>
          )}

          {actionMessage && (
            <div className="banner banner--success" style={{ marginBottom: 'var(--space-4)', borderRadius: '8px' }}>
              ✅ {actionMessage}
            </div>
          )}

          <div className="card" style={{ overflow: 'hidden' }}>
            <div className="tabs" role="tablist" aria-label="DLQ Navigation">
              {dlqTabs.map((t) => (
                <button
                  key={t.id}
                  type="button"
                  role="tab"
                  aria-selected={activeDlqTab === t.id}
                  className={`tab ${activeDlqTab === t.id ? 'tab--active' : ''}`}
                  onClick={() => setActiveDlqTab(t.id)}
                >
                  {t.label}
                </button>
              ))}
            </div>

            <div className="card__body" style={{ padding: 'var(--space-4)' }}>
              {dlqLoading ? (
                <div style={{ textAlign: 'center', padding: 'var(--space-12)', color: 'var(--text-secondary)' }}>
                  Loading logs and sync metrics...
                </div>
              ) : activeDlqTab === 'dlq' ? (
                <div>
                  {dlqRecords.length === 0 ? (
                    <div style={{ textAlign: 'center', padding: 'var(--space-12)' }}>
                      <span style={{ fontSize: '48px', display: 'block', marginBottom: 'var(--space-4)' }}>🎉</span>
                      <h4 style={{ fontWeight: 700, fontSize: 'var(--text-base)' }}>Dead Letter Queue is Empty</h4>
                      <p style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-sm)', margin: 0 }}>
                        All outbox events synchronized successfully with connected HRIS providers.
                      </p>
                    </div>
                  ) : (
                    <div style={{ overflowX: 'auto' }}>
                      <table className="table" style={{ width: '100%', borderCollapse: 'collapse' }}>
                        <thead>
                          <tr style={{ textAlign: 'left', borderBottom: '2px solid var(--border)' }}>
                            <th style={{ padding: 'var(--space-3) var(--space-4)', fontSize: 'var(--text-xs)', fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase' }}>Provider</th>
                            <th style={{ padding: 'var(--space-3) var(--space-4)', fontSize: 'var(--text-xs)', fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase' }}>Failure Reason</th>
                            <th style={{ padding: 'var(--space-3) var(--space-4)', fontSize: 'var(--text-xs)', fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase' }}>Created At</th>
                            <th style={{ padding: 'var(--space-3) var(--space-4)', fontSize: 'var(--text-xs)', fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase' }}>Status</th>
                            <th style={{ padding: 'var(--space-3) var(--space-4)', fontSize: 'var(--text-xs)', fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase', textAlign: 'right' }}>Actions</th>
                          </tr>
                        </thead>
                        <tbody>
                          {dlqRecords.map((rec) => (
                            <tr key={rec.id} style={{ borderBottom: '1px solid var(--border)' }}>
                              <td style={{ padding: 'var(--space-4)', fontSize: 'var(--text-sm)', fontWeight: 600 }}>{rec.provider.toUpperCase()}</td>
                              <td style={{ padding: 'var(--space-4)', fontSize: 'var(--text-sm)', color: 'var(--danger)' }}>
                                <div style={{ fontWeight: 650 }}>{rec.error_detail}</div>
                                <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: '2px' }}>Event Outbox ID: {rec.outbox_id}</div>
                              </td>
                              <td style={{ padding: 'var(--space-4)', fontSize: 'var(--text-xs)', color: 'var(--text-secondary)' }}>
                                {new Date(rec.created_at).toLocaleString()}
                              </td>
                              <td style={{ padding: 'var(--space-4)' }}>
                                <span className={`badge badge--${rec.status === 'resolved' ? 'hire' : 'reject'}`}>
                                  {rec.status}
                                </span>
                              </td>
                              <td style={{ padding: 'var(--space-4)', textAlign: 'right' }}>
                                {rec.status !== 'resolved' && (
                                  <button
                                    type="button"
                                    className="btn btn--primary btn--sm"
                                    onClick={() => handleRetry(rec.id)}
                                    style={{ borderRadius: '6px' }}
                                  >
                                    Retry Sync
                                  </button>
                                )}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              ) : (
                <div>
                  {syncMetrics.length === 0 ? (
                    <div style={{ textAlign: 'center', padding: 'var(--space-12)' }}>
                      <span style={{ fontSize: '48px', display: 'block', marginBottom: 'var(--space-4)' }}>📈</span>
                      <h4 style={{ fontWeight: 700, fontSize: 'var(--text-base)' }}>No Sync Metrics Recorded</h4>
                      <p style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-sm)', margin: 0 }}>
                        System sync metric snapshots will appear here as outbox flows execute.
                      </p>
                    </div>
                  ) : (
                    <div style={{ overflowX: 'auto' }}>
                      <table className="table" style={{ width: '100%', borderCollapse: 'collapse' }}>
                        <thead>
                          <tr style={{ textAlign: 'left', borderBottom: '2px solid var(--border)' }}>
                            <th style={{ padding: 'var(--space-3) var(--space-4)', fontSize: 'var(--text-xs)', fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase' }}>Sync Snapshot</th>
                            <th style={{ padding: 'var(--space-3) var(--space-4)', fontSize: 'var(--text-xs)', fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase' }}>Provider</th>
                            <th style={{ padding: 'var(--space-3) var(--space-4)', fontSize: 'var(--text-xs)', fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase' }}>Successful Syncs</th>
                            <th style={{ padding: 'var(--space-3) var(--space-4)', fontSize: 'var(--text-xs)', fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase' }}>Sync Failures</th>
                            <th style={{ padding: 'var(--space-3) var(--space-4)', fontSize: 'var(--text-xs)', fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase' }}>Health Ratio</th>
                          </tr>
                        </thead>
                        <tbody>
                          {syncMetrics.map((met) => {
                            const total = met.success_count + met.failure_count
                            const healthRatio = total > 0 ? ((met.success_count / total) * 100).toFixed(1) : '100'
                            return (
                              <tr key={met.id} style={{ borderBottom: '1px solid var(--border)' }}>
                                <td style={{ padding: 'var(--space-4)', fontSize: 'var(--text-xs)', color: 'var(--text-secondary)' }}>
                                  {new Date(met.timestamp).toLocaleString()}
                                </td>
                                <td style={{ padding: 'var(--space-4)', fontSize: 'var(--text-sm)', fontWeight: 600 }}>{met.provider.toUpperCase()}</td>
                                <td style={{ padding: 'var(--space-4)', fontSize: 'var(--text-sm)', color: 'var(--success)', fontWeight: 600 }}>{met.success_count}</td>
                                <td style={{ padding: 'var(--space-4)', fontSize: 'var(--text-sm)', color: 'var(--danger)', fontWeight: 600 }}>{met.failure_count}</td>
                                <td style={{ padding: 'var(--space-4)' }}>
                                  <span className={`badge badge--${parseFloat(healthRatio) >= 90 ? 'hire' : parseFloat(healthRatio) >= 50 ? 'interview' : 'reject'}`}>
                                    {healthRatio}%
                                  </span>
                                </td>
                              </tr>
                            )
                          })}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      </AppLayout>
    )
  }

  const { result, request } = state

  const tabs: { id: Tab; label: string }[] = [
    { id: 'documents', label: 'Documents' },
    { id: 'training', label: 'Training plan' },
    { id: 'email', label: 'Welcome email' },
  ]

  return (
    <AppLayout>
      <div className="container" style={{ padding: 'var(--space-8) 0 var(--space-16)' }}>
        <header className="page-header">
          <div>
            <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 'var(--space-3)', marginBottom: 'var(--space-2)' }}>
              <h1 className="page-header__title">{request.name}</h1>
              <span className="badge badge--neutral">{request.department}</span>
            </div>
            <p className="page-header__meta">
              {request.role} · Starts {request.start_date} · {request.email}
            </p>
          </div>
          <Link to="/dashboard" className="btn btn--secondary">
            Back to pipeline
          </Link>
        </header>

        <div className="card" style={{ overflow: 'hidden' }}>
          <div className="tabs" role="tablist" aria-label="Onboarding outputs">
            {tabs.map((t) => (
              <button
                key={t.id}
                type="button"
                role="tab"
                aria-selected={activeTab === t.id}
                className={`tab ${activeTab === t.id ? 'tab--active' : ''}`}
                onClick={() => setActiveTab(t.id)}
              >
                {t.label}
              </button>
            ))}
          </div>

          <div className="card__body markdown-body" role="tabpanel">
            {activeTab === 'documents' && (
              <div>
                {result.documents_generated.map((doc, idx) => (
                  <div key={idx} style={{ marginBottom: idx < result.documents_generated.length - 1 ? 40 : 0 }}>
                    <ReactMarkdown>{doc}</ReactMarkdown>
                    {idx < result.documents_generated.length - 1 && (
                      <hr style={{ border: 'none', borderTop: '1px solid var(--border)', margin: '40px 0' }} />
                    )}
                  </div>
                ))}
              </div>
            )}

            {activeTab === 'training' && <ReactMarkdown>{result.training_plan}</ReactMarkdown>}

            {activeTab === 'email' && <ReactMarkdown>{result.email_draft}</ReactMarkdown>}
          </div>
        </div>
      </div>
    </AppLayout>
  )
}
