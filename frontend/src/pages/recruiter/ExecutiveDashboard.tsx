import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../../api'

type Widget = {
  id: string
  label: string
  visible: boolean
}

const DEFAULT_WIDGETS: Widget[] = [
  { id: 'kpis', label: 'KPI Summary Cards', visible: true },
  { id: 'funnel', label: 'Hiring Funnel', visible: true },
  { id: 'sla', label: 'SLA Compliance', visible: true },
  { id: 'velocity', label: 'Hiring Velocity', visible: true },
  { id: 'sources', label: 'Hiring Sources', visible: true },
  { id: 'activity', label: 'Recent Activity', visible: true },
  { id: 'forecast', label: 'Quick Forecast', visible: true },
]

const STORAGE_KEY = 'exec_dashboard_widgets'

function loadWidgets(): Widget[] {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored) return JSON.parse(stored)
  } catch { /* ignore */ }
  return DEFAULT_WIDGETS
}

function saveWidgets(widgets: Widget[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(widgets))
}

export default function ExecutiveDashboard() {
  const navigate = useNavigate()

  const [overview, setOverview] = useState<Record<string, any> | null>(null)
  const [funnel, setFunnel] = useState<any | null>(null)
  const [sla, setSla] = useState<any | null>(null)
  const [forecast, setForecast] = useState<any | null>(null)
  const [sources, setSources] = useState<any[]>([])
  const [activity, setActivity] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [widgets, setWidgets] = useState<Widget[]>(loadWidgets)
  const [showCustomize, setShowCustomize] = useState(false)

  const fetchAll = useCallback(async () => {
    setLoading(true)
    try {
      const [ovRes, fnRes, slaRes, fcRes, srcRes, actRes] = await Promise.allSettled([
        api.get('/v1/executive/dashboard'),
        api.get('/v1/executive/funnel'),
        api.get('/v1/executive/sla-compliance'),
        api.get('/v1/executive/forecast?window_days=90'),
        api.get('/v1/executive/sources'),
        api.get('/v1/executive/recent-activity'),
      ])
      if (ovRes.status === 'fulfilled') setOverview(ovRes.value.data)
      if (fnRes.status === 'fulfilled') setFunnel(fnRes.value.data)
      if (slaRes.status === 'fulfilled') setSla(slaRes.value.data)
      if (fcRes.status === 'fulfilled') setForecast(fcRes.value.data)
      if (srcRes.status === 'fulfilled') setSources(srcRes.value.data?.sources || [])
      if (actRes.status === 'fulfilled') setActivity(actRes.value.data?.events || [])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchAll() }, [fetchAll])

  const toggleWidget = (id: string) => {
    const updated = widgets.map(w => w.id === id ? { ...w, visible: !w.visible } : w)
    setWidgets(updated)
    saveWidgets(updated)
  }

  const isVisible = (id: string) => widgets.find(w => w.id === id)?.visible !== false

  const kpiCards = overview ? [
    { label: 'Active Jobs', value: overview.active_jobs ?? '—', icon: '💼' },
    { label: 'Open Applications', value: overview.open_applications ?? '—', icon: '📋' },
    { label: 'Avg Time to Hire', value: `${overview.time_to_hire_days ?? 0}d`, icon: '⏱️' },
    { label: 'Offer Acceptance', value: `${overview.offer_acceptance_rate ?? 0}%`, icon: '✅' },
    { label: 'Interview Pass Rate', value: `${overview.interview_pass_rate ?? 0}%`, icon: '🎯' },
    { label: 'Awaiting Review', value: overview.candidates_awaiting_review ?? '—', icon: '👀' },
    { label: 'SLA Breaches', value: overview.sla_breach_count ?? '—', icon: '⚠️' },
    { label: 'Avg Time in Stage', value: `${overview.avg_time_in_stage_hours ?? 0}h`, icon: '📊' },
  ] : []

  const maxFunnelCount = funnel?.stages?.[0]?.candidate_count || 1

  return (
    <div style={styles.page}>
      {/* Header */}
      <div style={styles.header}>
        <div>
          <h1 style={styles.title}>Executive Dashboard</h1>
          <p style={styles.subtitle}>Hiring intelligence overview — organisation-wide metrics</p>
        </div>
        <div style={styles.headerActions}>
          <button id="exec-customize-btn" style={styles.btnSecondary} onClick={() => setShowCustomize(true)}>⚙️ Customize</button>
          <button id="exec-reports-btn" style={styles.btnPrimary} onClick={() => navigate('/recruiter/executive/reports')}>📄 Reports</button>
          <button id="exec-forecast-btn" style={styles.btnAccent} onClick={() => navigate('/recruiter/executive/forecast')}>🔮 Forecast</button>
        </div>
      </div>

      {loading && <div style={styles.loadingBar}><div style={styles.loadingFill} /></div>}

      {/* KPI Cards */}
      {isVisible('kpis') && (
        <div style={styles.kpiGrid}>
          {kpiCards.map(card => (
            <div key={card.label} style={styles.kpiCard}>
              <span style={styles.kpiIcon}>{card.icon}</span>
              <div style={styles.kpiValue}>{card.value}</div>
              <div style={styles.kpiLabel}>{card.label}</div>
            </div>
          ))}
        </div>
      )}

      <div style={styles.grid2col}>
        {/* Hiring Funnel */}
        {isVisible('funnel') && funnel && (
          <div style={styles.card}>
            <div style={styles.cardHeader}>
              <span style={styles.cardTitle}>🔻 Hiring Funnel</span>
              {funnel.bottleneck && funnel.bottleneck !== 'None' && (
                <span style={styles.bottleneckBadge}>⚠️ Bottleneck: {funnel.bottleneck}</span>
              )}
            </div>
            {funnel.stages?.map((stage: any) => (
              <div key={stage.stage} style={styles.funnelRow}>
                <span style={styles.funnelLabel}>{stage.stage}</span>
                <div style={styles.funnelBarTrack}>
                  <div style={{
                    ...styles.funnelBar,
                    width: `${Math.max(2, (stage.candidate_count / maxFunnelCount) * 100)}%`,
                    background: stage.drop_off_rate > 50
                      ? 'linear-gradient(90deg, #ff4d6d, #c9184a)'
                      : 'linear-gradient(90deg, #6c63ff, #8e85ff)',
                  }} />
                </div>
                <span style={styles.funnelCount}>{stage.candidate_count}</span>
                <span style={styles.funnelConv}>{stage.conversion_rate}%</span>
              </div>
            ))}
          </div>
        )}

        {/* SLA Compliance */}
        {isVisible('sla') && sla && (
          <div style={styles.card}>
            <div style={styles.cardHeader}><span style={styles.cardTitle}>📏 SLA Compliance</span></div>
            <div style={styles.donutWrapper}>
              <svg viewBox="0 0 100 100" style={styles.donut}>
                <circle cx="50" cy="50" r="40" fill="none" stroke="#1e2132" strokeWidth="12" />
                <circle
                  cx="50" cy="50" r="40" fill="none"
                  stroke={sla.compliance_rate >= 90 ? '#6c63ff' : sla.compliance_rate >= 70 ? '#f59e0b' : '#ef4444'}
                  strokeWidth="12"
                  strokeDasharray={`${sla.compliance_rate * 2.513} ${(100 - sla.compliance_rate) * 2.513}`}
                  strokeLinecap="round"
                  transform="rotate(-90 50 50)"
                />
                <text x="50" y="50" textAnchor="middle" dominantBaseline="central" fill="white" fontSize="18" fontWeight="bold">
                  {sla.compliance_rate}%
                </text>
              </svg>
            </div>
            <div style={styles.slaStats}>
              <div style={styles.slaStat}><span style={styles.slaNum}>{sla.total_trackers}</span><span style={styles.slaLbl}>Tracked</span></div>
              <div style={styles.slaStat}><span style={{ ...styles.slaNum, color: '#ef4444' }}>{sla.breached_count}</span><span style={styles.slaLbl}>Breached</span></div>
              <div style={styles.slaStat}><span style={{ ...styles.slaNum, color: '#f59e0b' }}>{sla.escalated_count}</span><span style={styles.slaLbl}>Escalated</span></div>
            </div>
          </div>
        )}

        {/* Forecast Quick View */}
        {isVisible('forecast') && forecast && (
          <div style={styles.card}>
            <div style={styles.cardHeader}>
              <span style={styles.cardTitle}>🔮 Forecast</span>
              <span style={styles.confidenceBadge}>{forecast.explanation?.confidence} Confidence</span>
            </div>
            <div style={styles.forecastGrid}>
              <div style={styles.forecastItem}>
                <div style={styles.forecastVal}>{forecast.forecast?.expected_hires}</div>
                <div style={styles.forecastLbl}>Expected Hires</div>
              </div>
              <div style={styles.forecastItem}>
                <div style={styles.forecastVal}>{forecast.forecast?.recruiter_capacity}</div>
                <div style={styles.forecastLbl}>Recruiter Capacity</div>
              </div>
              <div style={styles.forecastItem}>
                <div style={styles.forecastVal}>{forecast.forecast?.expected_time_to_fill_days}d</div>
                <div style={styles.forecastLbl}>Expected Time to Fill</div>
              </div>
              <div style={styles.forecastItem}>
                <div style={styles.forecastVal}>{forecast.explanation?.historical_average}/mo</div>
                <div style={styles.forecastLbl}>Historical Average</div>
              </div>
            </div>
            <button id="exec-view-forecast" style={styles.linkBtn} onClick={() => navigate('/recruiter/executive/forecast')}>
              View Full Forecast →
            </button>
          </div>
        )}

        {/* Hiring Sources */}
        {isVisible('sources') && sources.length > 0 && (
          <div style={styles.card}>
            <div style={styles.cardHeader}><span style={styles.cardTitle}>🌐 Hiring Sources</span></div>
            <div style={styles.tableWrapper}>
              <table style={styles.table}>
                <thead><tr>
                  {['Source', 'Apps', 'Interviews', 'Offers', 'Hires', 'Conv%'].map(h => (
                    <th key={h} style={styles.th}>{h}</th>
                  ))}
                </tr></thead>
                <tbody>
                  {sources.filter(s => s.applications > 0).slice(0, 6).map((s: any) => (
                    <tr key={s.source} style={styles.tr}>
                      <td style={styles.td}>{s.source}</td>
                      <td style={styles.td}>{s.applications}</td>
                      <td style={styles.td}>{s.interviews}</td>
                      <td style={styles.td}>{s.offers}</td>
                      <td style={styles.td}>{s.hires}</td>
                      <td style={{ ...styles.td, color: '#6c63ff', fontWeight: 600 }}>{s.conversion_rate}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      {/* Recent Activity */}
      {isVisible('activity') && activity.length > 0 && (
        <div style={styles.card}>
          <div style={styles.cardHeader}><span style={styles.cardTitle}>🕐 Recent Activity</span></div>
          <div style={styles.activityList}>
            {activity.map((e: any) => (
              <div key={e.id} style={styles.activityItem}>
                <div style={styles.activityDot} />
                <div>
                  <div style={styles.activityDetail}>{e.details}</div>
                  <div style={styles.activityMeta}>{e.actor_name} · {new Date(e.timestamp).toLocaleString()}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Customize Modal */}
      {showCustomize && (
        <div style={styles.overlay} onClick={() => setShowCustomize(false)}>
          <div style={styles.modal} onClick={e => e.stopPropagation()}>
            <h3 style={styles.modalTitle}>Customize Dashboard</h3>
            <p style={styles.modalSub}>Toggle which widgets are visible. Changes are saved automatically.</p>
            {widgets.map(w => (
              <div key={w.id} style={styles.widgetRow}>
                <label style={styles.widgetLabel}>
                  <input type="checkbox" checked={w.visible} onChange={() => toggleWidget(w.id)} style={styles.checkbox} />
                  {w.label}
                </label>
              </div>
            ))}
            <button style={styles.btnPrimary} onClick={() => setShowCustomize(false)}>Done</button>
          </div>
        </div>
      )}
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  page: { minHeight: '100vh', background: '#0f1117', color: '#e0e0e0', fontFamily: "'Inter', sans-serif", padding: '32px' },
  header: { display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 32, flexWrap: 'wrap', gap: 16 },
  title: { fontSize: 28, fontWeight: 800, margin: 0, background: 'linear-gradient(135deg, #6c63ff, #8e85ff)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' },
  subtitle: { color: '#888', fontSize: 14, marginTop: 4 },
  headerActions: { display: 'flex', gap: 10 },
  btnPrimary: { padding: '10px 20px', borderRadius: 10, border: 'none', background: '#6c63ff', color: '#fff', cursor: 'pointer', fontWeight: 600, fontSize: 14 },
  btnSecondary: { padding: '10px 20px', borderRadius: 10, border: '1px solid #2d3250', background: 'transparent', color: '#e0e0e0', cursor: 'pointer', fontWeight: 600, fontSize: 14 },
  btnAccent: { padding: '10px 20px', borderRadius: 10, border: 'none', background: 'linear-gradient(135deg, #06b6d4, #0e7490)', color: '#fff', cursor: 'pointer', fontWeight: 600, fontSize: 14 },
  loadingBar: { height: 3, background: '#1e2132', borderRadius: 2, marginBottom: 24, overflow: 'hidden' },
  loadingFill: { height: '100%', width: '60%', background: 'linear-gradient(90deg, #6c63ff, #8e85ff)', borderRadius: 2 },
  kpiGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: 16, marginBottom: 24 },
  kpiCard: { background: 'linear-gradient(135deg, #1a1d2e, #1e2132)', borderRadius: 16, padding: '20px 16px', textAlign: 'center', border: '1px solid #2d3250' },
  kpiIcon: { fontSize: 24, display: 'block', marginBottom: 8 },
  kpiValue: { fontSize: 26, fontWeight: 800, color: '#8e85ff', marginBottom: 4 },
  kpiLabel: { fontSize: 12, color: '#888', textTransform: 'uppercase', letterSpacing: 0.5 },
  grid2col: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(480px, 1fr))', gap: 20, marginBottom: 20 },
  card: { background: '#1a1d2e', borderRadius: 16, padding: 24, border: '1px solid #2d3250' },
  cardHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 },
  cardTitle: { fontSize: 16, fontWeight: 700, color: '#e0e0e0' },
  bottleneckBadge: { background: 'rgba(239,68,68,0.15)', color: '#ef4444', borderRadius: 8, padding: '4px 10px', fontSize: 12, fontWeight: 600 },
  confidenceBadge: { background: 'rgba(108,99,255,0.15)', color: '#8e85ff', borderRadius: 8, padding: '4px 10px', fontSize: 12, fontWeight: 600 },
  funnelRow: { display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 },
  funnelLabel: { width: 90, fontSize: 13, color: '#aaa' },
  funnelBarTrack: { flex: 1, height: 10, background: '#0f1117', borderRadius: 5, overflow: 'hidden' },
  funnelBar: { height: '100%', borderRadius: 5, transition: 'width 0.6s ease' },
  funnelCount: { width: 36, textAlign: 'right', fontSize: 13, fontWeight: 600 },
  funnelConv: { width: 40, textAlign: 'right', fontSize: 12, color: '#6c63ff' },
  donutWrapper: { display: 'flex', justifyContent: 'center', marginBottom: 16 },
  donut: { width: 140, height: 140 },
  slaStats: { display: 'flex', justifyContent: 'space-around' },
  slaStat: { textAlign: 'center' },
  slaNum: { display: 'block', fontSize: 24, fontWeight: 800, color: '#6c63ff' },
  slaLbl: { fontSize: 12, color: '#888' },
  forecastGrid: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 12 },
  forecastItem: { background: '#0f1117', borderRadius: 10, padding: '14px 12px', textAlign: 'center' },
  forecastVal: { fontSize: 22, fontWeight: 800, color: '#8e85ff' },
  forecastLbl: { fontSize: 11, color: '#888', marginTop: 4 },
  linkBtn: { background: 'none', border: 'none', color: '#6c63ff', cursor: 'pointer', fontSize: 13, fontWeight: 600, padding: 0 },
  tableWrapper: { overflowX: 'auto' },
  table: { width: '100%', borderCollapse: 'collapse', fontSize: 13 },
  th: { padding: '8px 12px', textAlign: 'left', color: '#888', fontWeight: 600, borderBottom: '1px solid #2d3250', fontSize: 12 },
  tr: { borderBottom: '1px solid #1e2132' },
  td: { padding: '8px 12px', color: '#e0e0e0' },
  activityList: { display: 'flex', flexDirection: 'column', gap: 12 },
  activityItem: { display: 'flex', gap: 12, alignItems: 'flex-start' },
  activityDot: { width: 8, height: 8, borderRadius: '50%', background: '#6c63ff', marginTop: 5, flexShrink: 0 },
  activityDetail: { fontSize: 13, color: '#e0e0e0' },
  activityMeta: { fontSize: 11, color: '#666', marginTop: 2 },
  overlay: { position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 },
  modal: { background: '#1a1d2e', borderRadius: 16, padding: 32, width: 400, border: '1px solid #2d3250', maxHeight: '80vh', overflowY: 'auto' },
  modalTitle: { margin: '0 0 8px', fontSize: 18, fontWeight: 700 },
  modalSub: { color: '#888', fontSize: 13, marginBottom: 20 },
  widgetRow: { marginBottom: 14 },
  widgetLabel: { display: 'flex', alignItems: 'center', gap: 10, cursor: 'pointer', fontSize: 14 },
  checkbox: { width: 16, height: 16, accentColor: '#6c63ff' },
}
