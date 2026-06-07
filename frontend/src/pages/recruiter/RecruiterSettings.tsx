import { useState, useEffect, useCallback } from 'react'
import AppLayout from '../../components/AppLayout'
import { 
  fetchCompany, 
  fetchDlqRecords, 
  fetchSyncMetrics, 
  retryDlqRecord, 
  type Company 
} from '../../api'

type DlqTab = 'dlq' | 'metrics'

export default function RecruiterSettings() {
  const [company, setCompany] = useState<Company | null>(null)
  const [loading, setLoading] = useState(true)

  // DLQ States
  const [activeDlqTab, setActiveDlqTab] = useState<DlqTab>('dlq')
  const [dlqRecords, setDlqRecords] = useState<any[]>([])
  const [syncMetrics, setSyncMetrics] = useState<any[]>([])
  const [dlqLoading, setDlqLoading] = useState(false)
  const [dlqError, setDlqError] = useState<string | null>(null)
  const [actionMessage, setActionMessage] = useState<string | null>(null)

  const loadDlqData = useCallback(async () => {
    setDlqLoading(true)
    setDlqError(null)
    try {
      const [records, metrics] = await Promise.all([
        fetchDlqRecords().catch(() => []),
        fetchSyncMetrics().catch(() => [])
      ])
      setDlqRecords(records)
      setSyncMetrics(metrics)
    } catch (err: any) {
      setDlqError(err.response?.data?.detail || 'Failed to retrieve DLQ and metrics logs.')
    } finally {
      setDlqLoading(false)
    }
  }, [])

  useEffect(() => {
    setLoading(true)
    fetchCompany()
      .then(co => setCompany(co))
      .catch(err => console.error('Error fetching company details:', err))
      .finally(() => setLoading(false))

    loadDlqData()
  }, [loadDlqData])

  const handleRetry = async (recordId: string) => {
    setActionMessage(null)
    setDlqError(null)
    try {
      await retryDlqRecord(recordId)
      setActionMessage('Sync retry request successfully submitted!')
      await loadDlqData()
    } catch (err: any) {
      setDlqError(err.response?.data?.detail || 'Failed to retry sync outbox event.')
    }
  }

  const dlqTabs: { id: DlqTab; label: string }[] = [
    { id: 'dlq', label: 'Dead Letter Queue (Errors)' },
    { id: 'metrics', label: 'Sync Metrics & Trends' },
  ]

  return (
    <AppLayout>
      <div className="container" style={{ padding: 'var(--space-6) 0 var(--space-12)' }}>
        {/* Header */}
        <div style={{
          borderBottom: '1px dashed var(--color-cork-shadow)',
          paddingBottom: 'var(--space-6)',
          marginBottom: 'var(--space-6)'
        }}>
          <span style={{ fontSize: 10, fontWeight: 500, color: 'var(--text-secondary)', letterSpacing: '0.05em', textTransform: 'uppercase' }}>
            Recruiter Control Center
          </span>
          <h1 style={{ fontSize: '29px', fontWeight: 500, letterSpacing: '-0.02em', color: 'var(--text)', margin: '4px 0 0', lineHeight: 1.09 }}>
            Workspace Settings
          </h1>
        </div>

        {loading ? (
          <div style={{ padding: 'var(--space-12) 0', textAlign: 'center', color: 'var(--text-secondary)' }}>
            Loading settings configurations...
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-8)' }}>
            {/* Top Config Cards Grid */}
            <div style={{ display: 'grid', gridTemplateColumns: '3fr 2fr', gap: 'var(--space-6)', alignItems: 'flex-start' }}>
              {/* Main Config Cards */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)' }}>
                
                {/* Profile Config Card */}
                <div style={{
                  border: '1px solid var(--color-cork-shadow)',
                  borderRadius: 12,
                  padding: 'var(--space-6)'
                }}>
                  <h2 style={{ fontSize: '18px', fontWeight: 500, margin: '0 0 16px', color: 'var(--text)' }}>
                    Workspace Profile
                  </h2>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                    <div>
                      <label style={{ display: 'block', fontSize: 10, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 4 }}>
                        Organization Name
                      </label>
                      <div style={{ fontSize: 15, color: 'var(--text)', paddingBottom: 4, borderBottom: '1px solid var(--color-cork-shadow)' }}>
                        {company?.name || 'SmartOnboard Partner'}
                      </div>
                    </div>
                    <div>
                      <label style={{ display: 'block', fontSize: 10, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 4 }}>
                        Workspace Domain
                      </label>
                      <div style={{ fontSize: 15, color: 'var(--text)', paddingBottom: 4, borderBottom: '1px solid var(--color-cork-shadow)' }}>
                        {company?.slug ? `${company.slug}.com` : 'smartonboard.io'}
                      </div>
                    </div>
                  </div>
                </div>

                {/* DNS Verification Center */}
                <div style={{
                  border: '1px solid var(--color-cork-shadow)',
                  borderRadius: 12,
                  padding: 'var(--space-6)'
                }}>
                  <h2 style={{ fontSize: '18px', fontWeight: 500, margin: '0 0 16px', color: 'var(--text)' }}>
                    MX / DNS Domain Verification
                  </h2>
                  <p style={{ fontSize: 14, color: 'var(--text-secondary)', lineHeight: 1.33, margin: '0 0 16px' }}>
                    Verify company email domain records to secure workspace operations and candidate communication channels.
                  </p>
                  <div style={{
                    border: '1px dashed var(--color-cork-shadow)',
                    borderRadius: 12,
                    padding: 16,
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center'
                  }}>
                    <div>
                      <div style={{ fontSize: 14, fontWeight: 500 }}>MX Domain State: <span style={{ color: 'var(--color-burnt-sienna)' }}>Pending Verification</span></div>
                      <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 2 }}>Expected MX domain record: mail.{company?.slug ? `${company.slug}.com` : 'smartonboard.io'}</div>
                    </div>
                    <button className="btn btn--secondary btn--sm" style={{ borderRadius: 22.5 }} onClick={() => alert('Initiating background domain verification check...')}>
                      Verify Records
                    </button>
                  </div>
                </div>
              </div>

              {/* Right Sidebar Columns */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)' }}>
                
                {/* Billing Placeholder Card */}
                <div style={{
                  border: '1px solid var(--color-warm-cream)',
                  borderRadius: 12,
                  padding: 'var(--space-6)',
                  background: 'transparent'
                }}>
                  <h2 style={{ fontSize: '18px', fontWeight: 500, margin: '0 0 12px', color: 'var(--text)' }}>
                    Subscription & Billing
                  </h2>
                  <div style={{
                    fontSize: 10,
                    fontWeight: 500,
                    color: 'var(--color-burnt-sienna)',
                    letterSpacing: '0.05em',
                    textTransform: 'uppercase',
                    marginBottom: 12
                  }}>
                    Coming Soon
                  </div>
                  <p style={{ fontSize: 13, lineHeight: 1.35, color: 'var(--text-secondary)', margin: 0 }}>
                    SmartOnboard platform subscription controls, invoice tracking, plan selectors, and payment gateway configurations will be made available in the next release cycle.
                  </p>
                  <div style={{ borderTop: '1px dashed var(--color-cork-shadow)', marginTop: 16, paddingTop: 16, fontSize: 12, color: 'var(--text-secondary)' }}>
                    Planned Plan Rates: <strong>$49/month per active job</strong>
                  </div>
                </div>
              </div>
            </div>

            {/* DLQ Monitoring and Retry Section */}
            <div style={{
              border: '1px dashed var(--color-cork-shadow)',
              borderRadius: 12,
              padding: 'var(--space-6)',
              marginTop: 'var(--space-4)'
            }}>
              <h2 style={{ fontSize: '18px', fontWeight: 500, margin: '0 0 8px', color: 'var(--text)' }}>
                HRIS Outbox logs & Dead Letter Queue (DLQ)
              </h2>
              <p style={{ color: 'var(--color-grey-brown)', fontSize: '14px', lineHeight: 1.33, margin: '0 0 20px' }}>
                Inspect failed transfers in the Dead Letter Queue, view system sync counters, and trigger manual retries.
              </p>

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

              <div className="card" style={{ background: 'transparent', border: '1px solid var(--color-cork-shadow)', borderRadius: '8px', boxShadow: 'none', overflow: 'hidden' }}>
                <div className="tabs" role="tablist" aria-label="DLQ Navigation" style={{ display: 'flex', borderBottom: '1px solid var(--color-cork-shadow)' }}>
                  {dlqTabs.map((t) => (
                    <button
                      key={t.id}
                      type="button"
                      role="tab"
                      aria-selected={activeDlqTab === t.id}
                      className={`tab ${activeDlqTab === t.id ? 'tab--active' : ''}`}
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
                                  <td style={{ padding: 'var(--space-4)', fontSize: '14px', fontWeight: 500, color: 'var(--text)' }}>{(rec.provider || '').toUpperCase()}</td>
                                  <td style={{ padding: 'var(--space-4)', fontSize: '14px', color: 'var(--color-burnt-sienna)' }}>
                                    <div style={{ fontWeight: 500 }}>{rec.error_detail || rec.error_message || 'Connection timeout or invalid sync parameters'}</div>
                                    <div style={{ fontSize: '10px', color: 'var(--color-grey-brown)', marginTop: '2px' }}>Event Outbox ID: {rec.outbox_id || rec.id}</div>
                                  </td>
                                  <td style={{ padding: 'var(--space-4)', fontSize: '12px', color: 'var(--color-grey-brown)' }}>
                                    {new Date(rec.created_at || Date.now()).toLocaleString()}
                                  </td>
                                  <td style={{ padding: 'var(--space-4)' }}>
                                    <span className="badge" style={{ border: rec.status === 'resolved' || rec.resolved_at ? '1px solid var(--color-warm-cream)' : '1px solid var(--color-burnt-sienna)', color: rec.status === 'resolved' || rec.resolved_at ? 'var(--text)' : 'var(--color-burnt-sienna)', padding: '2px 8px', fontSize: '10px', borderRadius: '999px', background: 'transparent' }}>
                                      {rec.resolved_at ? 'resolved' : (rec.status || 'failed')}
                                    </span>
                                  </td>
                                  <td style={{ padding: 'var(--space-4)', textAlign: 'right' }}>
                                    {!rec.resolved_at && rec.status !== 'resolved' && (
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
                                      {new Date(met.timestamp || met.created_at || Date.now()).toLocaleString()}
                                    </td>
                                    <td style={{ padding: 'var(--space-4)', fontSize: '14px', fontWeight: 500, color: 'var(--text)' }}>{(met.provider || '').toUpperCase()}</td>
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
          </div>
        )}
      </div>
    </AppLayout>
  )
}
