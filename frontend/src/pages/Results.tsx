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
          <header className="page-header" style={{ marginBottom: 'var(--space-6)', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <div>
              <h1 style={{ fontSize: '29px', fontWeight: 500, letterSpacing: '-0.02em', marginBottom: '4px', lineHeight: 1.09, color: 'var(--text)' }}>HRIS Sync Logs & Outbox DLQ</h1>
              <p style={{ color: 'var(--color-grey-brown)', fontSize: '14px', lineHeight: 1.33, margin: 0 }}>
                Inspect failed transfers in the Dead Letter Queue, view system sync counters, and trigger manual retries.
              </p>
            </div>
            <Link to="/dashboard" className="btn btn--secondary" style={{ borderRadius: '22.5px', border: '1px solid var(--color-warm-cream)', background: 'transparent', color: 'var(--text)', padding: '8px 16px', fontSize: '12px' }}>
              Back to Dashboard
            </Link>
          </header>

          {dlqError && (
            <div className="banner banner--error" style={{ border: '1px solid var(--color-burnt-sienna)', background: 'transparent', color: 'var(--color-burnt-sienna)', padding: 'var(--space-3) var(--space-4)', borderRadius: '0px', marginBottom: 'var(--space-4)', fontSize: '12px' }}>
              ❌ {dlqError}
            </div>
          )}

          {actionMessage && (
            <div className="banner banner--success" style={{ border: '1px solid var(--color-warm-cream)', background: 'transparent', color: 'var(--text)', padding: 'var(--space-3) var(--space-4)', borderRadius: '0px', marginBottom: 'var(--space-4)', fontSize: '12px' }}>
              ✅ {actionMessage}
            </div>
          )}

          <div className="card" style={{ background: 'transparent', border: '1px dashed var(--color-cork-shadow)', borderRadius: '12px', boxShadow: 'none', overflow: 'hidden' }}>
            <div className="tabs" role="tablist" aria-label="DLQ Navigation" style={{ display: 'flex', borderBottom: '1px solid var(--color-cork-shadow)' }}>
              {dlqTabs.map((t) => (
                <button
                  key={t.id}
                  type="button"
                  role="tab"
                  aria-selected={activeDlqTab === t.id}
                  className="tab"
                  style={{
                    padding: '12px 18px',
                    fontSize: '12px',
                    fontFamily: 'inherit',
                    fontWeight: 500,
                    border: 'none',
                    borderBottom: activeDlqTab === t.id ? '2px solid var(--color-burnt-sienna)' : '2px solid transparent',
                    background: 'transparent',
                    color: activeDlqTab === t.id ? 'var(--text)' : 'var(--color-grey-brown)',
                    cursor: 'pointer',
                    borderRadius: '0px'
                  }}
                  onClick={() => setActiveDlqTab(t.id)}
                >
                  {t.label}
                </button>
              ))}
            </div>

            <div className="card__body" style={{ padding: 'var(--space-4)' }}>
              {dlqLoading ? (
                <div style={{ textAlign: 'center', padding: 'var(--space-12)', color: 'var(--color-grey-brown)', fontSize: '14px' }}>
                  Loading logs and sync metrics...
                </div>
              ) : activeDlqTab === 'dlq' ? (
                <div>
                  {dlqRecords.length === 0 ? (
                    <div style={{ textAlign: 'center', padding: 'var(--space-12) var(--space-4)' }}>
                      <span style={{ fontSize: '48px', display: 'block', marginBottom: 'var(--space-4)' }}>🎉</span>
                      <h4 style={{ fontWeight: 500, fontSize: '18px', color: 'var(--text)', margin: '0 0 var(--space-2) 0' }}>Dead Letter Queue is Empty</h4>
                      <p style={{ color: 'var(--color-grey-brown)', fontSize: '14px', margin: 0 }}>
                        All outbox events synchronized successfully with connected HRIS providers.
                      </p>
                    </div>
                  ) : (
                    <div style={{ overflowX: 'auto' }}>
                      <table className="table" style={{ width: '100%', borderCollapse: 'collapse' }}>
                        <thead>
                          <tr style={{ textAlign: 'left', borderBottom: '1px dashed var(--color-cork-shadow)' }}>
                            <th style={{ padding: 'var(--space-3) var(--space-4)', fontSize: '10px', fontWeight: 500, color: 'var(--color-grey-brown)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Provider</th>
                            <th style={{ padding: 'var(--space-3) var(--space-4)', fontSize: '10px', fontWeight: 500, color: 'var(--color-grey-brown)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Failure Reason</th>
                            <th style={{ padding: 'var(--space-3) var(--space-4)', fontSize: '10px', fontWeight: 500, color: 'var(--color-grey-brown)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Created At</th>
                            <th style={{ padding: 'var(--space-3) var(--space-4)', fontSize: '10px', fontWeight: 500, color: 'var(--color-grey-brown)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Status</th>
                            <th style={{ padding: 'var(--space-3) var(--space-4)', fontSize: '10px', fontWeight: 500, color: 'var(--color-grey-brown)', textTransform: 'uppercase', letterSpacing: '0.05em', textAlign: 'right' }}>Actions</th>
                          </tr>
                        </thead>
                        <tbody>
                          {dlqRecords.map((rec) => (
                            <tr key={rec.id} style={{ borderBottom: '1px dashed var(--color-cork-shadow)' }}>
                              <td style={{ padding: 'var(--space-4)', fontSize: '14px', fontWeight: 500, color: 'var(--text)' }}>{rec.provider.toUpperCase()}</td>
                              <td style={{ padding: 'var(--space-4)', fontSize: '14px', color: 'var(--color-burnt-sienna)' }}>
                                <div style={{ fontWeight: 500 }}>{rec.error_detail}</div>
                                <div style={{ fontSize: '10px', color: 'var(--color-grey-brown)', marginTop: '2px' }}>Event Outbox ID: {rec.outbox_id}</div>
                              </td>
                              <td style={{ padding: 'var(--space-4)', fontSize: '12px', color: 'var(--color-grey-brown)' }}>
                                {new Date(rec.created_at).toLocaleString()}
                              </td>
                              <td style={{ padding: 'var(--space-4)' }}>
                                <span className="badge" style={{ border: rec.status === 'resolved' ? '1px solid var(--color-warm-cream)' : '1px solid var(--color-burnt-sienna)', color: rec.status === 'resolved' ? 'var(--text)' : 'var(--color-burnt-sienna)', padding: '2px 8px', fontSize: '10px', borderRadius: '999px', background: 'transparent' }}>
                                  {rec.status}
                                </span>
                              </td>
                              <td style={{ padding: 'var(--space-4)', textAlign: 'right' }}>
                                {rec.status !== 'resolved' && (
                                  <button
                                    type="button"
                                    className="btn btn--primary btn--sm"
                                    onClick={() => handleRetry(rec.id)}
                                    style={{ borderRadius: '22.5px', border: '1px solid var(--color-warm-cream)', background: 'transparent', color: 'var(--text)', padding: '4px 10px', fontSize: '11px', boxShadow: 'none' }}
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
                    <div style={{ textAlign: 'center', padding: 'var(--space-12) var(--space-4)' }}>
                      <span style={{ fontSize: '48px', display: 'block', marginBottom: 'var(--space-4)' }}>📈</span>
                      <h4 style={{ fontWeight: 500, fontSize: '18px', color: 'var(--text)', margin: '0 0 var(--space-2) 0' }}>No Sync Metrics Recorded</h4>
                      <p style={{ color: 'var(--color-grey-brown)', fontSize: '14px', margin: 0 }}>
                        System sync metric snapshots will appear here as outbox flows execute.
                      </p>
                    </div>
                  ) : (
                    <div style={{ overflowX: 'auto' }}>
                      <table className="table" style={{ width: '100%', borderCollapse: 'collapse' }}>
                        <thead>
                          <tr style={{ textAlign: 'left', borderBottom: '1px dashed var(--color-cork-shadow)' }}>
                            <th style={{ padding: 'var(--space-3) var(--space-4)', fontSize: '10px', fontWeight: 500, color: 'var(--color-grey-brown)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Sync Snapshot</th>
                            <th style={{ padding: 'var(--space-3) var(--space-4)', fontSize: '10px', fontWeight: 500, color: 'var(--color-grey-brown)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Provider</th>
                            <th style={{ padding: 'var(--space-3) var(--space-4)', fontSize: '10px', fontWeight: 500, color: 'var(--color-grey-brown)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Successful Syncs</th>
                            <th style={{ padding: 'var(--space-3) var(--space-4)', fontSize: '10px', fontWeight: 500, color: 'var(--color-grey-brown)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Sync Failures</th>
                            <th style={{ padding: 'var(--space-3) var(--space-4)', fontSize: '10px', fontWeight: 500, color: 'var(--color-grey-brown)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Health Ratio</th>
                          </tr>
                        </thead>
                        <tbody>
                          {syncMetrics.map((met) => {
                            const total = met.success_count + met.failure_count
                            const healthRatio = total > 0 ? ((met.success_count / total) * 100).toFixed(1) : '100'
                            const ratioVal = parseFloat(healthRatio)
                            return (
                              <tr key={met.id} style={{ borderBottom: '1px dashed var(--color-cork-shadow)' }}>
                                <td style={{ padding: 'var(--space-4)', fontSize: '12px', color: 'var(--color-grey-brown)' }}>
                                  {new Date(met.timestamp).toLocaleString()}
                                </td>
                                <td style={{ padding: 'var(--space-4)', fontSize: '14px', fontWeight: 500, color: 'var(--text)' }}>{met.provider.toUpperCase()}</td>
                                <td style={{ padding: 'var(--space-4)', fontSize: '14px', color: 'var(--text)', fontWeight: 500 }}>{met.success_count}</td>
                                <td style={{ padding: 'var(--space-4)', fontSize: '14px', color: 'var(--color-burnt-sienna)', fontWeight: 500 }}>{met.failure_count}</td>
                                <td style={{ padding: 'var(--space-4)' }}>
                                  <span className="badge" style={{ border: ratioVal >= 90 ? '1px solid var(--color-warm-cream)' : '1px solid var(--color-burnt-sienna)', color: ratioVal >= 90 ? 'var(--text)' : 'var(--color-burnt-sienna)', padding: '2px 8px', fontSize: '10px', borderRadius: '999px', background: 'transparent' }}>
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
        <header className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 'var(--space-6)' }}>
          <div>
            <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 'var(--space-3)', marginBottom: 'var(--space-2)' }}>
              <h1 style={{ fontSize: '29px', fontWeight: 500, letterSpacing: '-0.02em', margin: 0, color: 'var(--text)' }}>{request.name}</h1>
              <span className="badge" style={{ border: '1px solid var(--color-cork-shadow)', padding: '2px 8px', fontSize: '10px', borderRadius: '0px', background: 'transparent', color: 'var(--color-grey-brown)' }}>{request.department}</span>
            </div>
            <p style={{ color: 'var(--color-grey-brown)', fontSize: '14px', lineHeight: 1.33, margin: 0 }}>
              {request.role} · Starts {request.start_date} · {request.email}
            </p>
          </div>
          <Link to="/dashboard" className="btn btn--secondary" style={{ borderRadius: '22.5px', border: '1px solid var(--color-warm-cream)', background: 'transparent', color: 'var(--text)', padding: '8px 16px', fontSize: '12px' }}>
            Back to pipeline
          </Link>
        </header>

        <div className="card" style={{ background: 'transparent', border: '1px dashed var(--color-cork-shadow)', borderRadius: '12px', boxShadow: 'none', overflow: 'hidden' }}>
          <div className="tabs" role="tablist" aria-label="Onboarding outputs" style={{ display: 'flex', borderBottom: '1px solid var(--color-cork-shadow)' }}>
            {tabs.map((t) => (
              <button
                key={t.id}
                type="button"
                role="tab"
                aria-selected={activeTab === t.id}
                style={{
                  padding: '12px 18px',
                  fontSize: '12px',
                  fontFamily: 'inherit',
                  fontWeight: 500,
                  border: 'none',
                  borderBottom: activeTab === t.id ? '2px solid var(--color-burnt-sienna)' : '2px solid transparent',
                  background: 'transparent',
                  color: activeTab === t.id ? 'var(--text)' : 'var(--color-grey-brown)',
                  cursor: 'pointer',
                  borderRadius: '0px'
                }}
                onClick={() => setActiveTab(t.id)}
              >
                {t.label}
              </button>
            ))}
          </div>

          <div className="card__body markdown-body" role="tabpanel" style={{ padding: 'var(--space-6)', color: 'var(--text)', fontSize: '14px', lineHeight: 1.33 }}>
            {activeTab === 'documents' && (
              <div>
                {result.documents_generated.map((doc, idx) => (
                  <div key={idx} style={{ marginBottom: idx < result.documents_generated.length - 1 ? 40 : 0 }}>
                    <ReactMarkdown>{doc}</ReactMarkdown>
                    {idx < result.documents_generated.length - 1 && (
                      <hr style={{ border: 'none', borderTop: '1px dashed var(--color-cork-shadow)', margin: '40px 0' }} />
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
