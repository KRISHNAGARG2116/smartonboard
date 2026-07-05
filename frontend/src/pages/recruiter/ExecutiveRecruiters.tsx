import { useState, useEffect } from 'react'
import { api } from '../../api'

export default function ExecutiveRecruiters() {
  const [recruiters, setRecruiters] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [sortKey, setSortKey] = useState<string>('hires_made')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc')

  useEffect(() => {
    api.get('/v1/executive/recruiters')
      .then(r => { if (r.data?.recruiters) setRecruiters(r.data.recruiters) })
      .finally(() => setLoading(false))
  }, [])

  const sorted = [...recruiters].sort((a, b) => {
    const av = typeof a[sortKey] === 'number' ? a[sortKey] : 0
    const bv = typeof b[sortKey] === 'number' ? b[sortKey] : 0
    return sortDir === 'desc' ? bv - av : av - bv
  })

  const handleSort = (key: string) => {
    if (sortKey === key) setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    else { setSortKey(key); setSortDir('desc') }
  }

  const cols = [
    { key: 'recruiter_name', label: 'Recruiter', numeric: false },
    { key: 'candidates_reviewed', label: 'Reviewed', numeric: true },
    { key: 'interviews_scheduled', label: 'Interviews', numeric: true },
    { key: 'hires_made', label: 'Hires', numeric: true },
    { key: 'scorecard_completion_rate', label: 'Scorecard %', numeric: true },
    { key: 'sla_compliance_rate', label: 'SLA %', numeric: true },
  ]

  const bar = (val: number, max: number, color: string) => (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <div style={{ flex: 1, height: 6, background: '#0f1117', borderRadius: 3, overflow: 'hidden', minWidth: 60 }}>
        <div style={{ height: '100%', width: `${Math.min(100, (val / max) * 100)}%`, background: color, borderRadius: 3, transition: 'width 0.5s' }} />
      </div>
      <span style={{ fontSize: 12, fontWeight: 600, color: '#e0e0e0', minWidth: 32 }}>{typeof val === 'number' ? (Number.isInteger(val) ? val : val.toFixed(1)) : val}</span>
    </div>
  )

  const maxReviewed = Math.max(...recruiters.map(r => r.candidates_reviewed || 0), 1)
  const maxInterviews = Math.max(...recruiters.map(r => r.interviews_scheduled || 0), 1)
  const maxHires = Math.max(...recruiters.map(r => r.hires_made || 0), 1)

  return (
    <div style={styles.page}>
      <div style={styles.header}>
        <div>
          <h1 style={styles.title}>Recruiter Performance</h1>
          <p style={styles.subtitle}>Productivity leaderboard and SLA compliance metrics</p>
        </div>
      </div>

      {loading ? (
        <div style={styles.loadingPulse}>Loading recruiter data…</div>
      ) : recruiters.length === 0 ? (
        <div style={styles.empty}>No recruiter data available yet.</div>
      ) : (
        <>
          {/* Leaderboard Cards */}
          <div style={styles.leaderGrid}>
            {sorted.slice(0, 3).map((r, i) => (
              <div key={r.recruiter_id} style={{ ...styles.leaderCard, border: i === 0 ? '1px solid #6c63ff' : '1px solid #2d3250' }}>
                <div style={styles.medal}>{['🥇', '🥈', '🥉'][i]}</div>
                <div style={styles.leaderName}>{r.recruiter_name}</div>
                <div style={styles.leaderStat}>{r.hires_made} hires · {r.sla_compliance_rate}% SLA</div>
                <div style={styles.leaderMini}>
                  <span>Reviews: <b>{r.candidates_reviewed}</b></span>
                  <span>Interviews: <b>{r.interviews_scheduled}</b></span>
                </div>
              </div>
            ))}
          </div>

          {/* Full Table */}
          <div style={styles.tableCard}>
            <table style={styles.table}>
              <thead>
                <tr>
                  {cols.map(c => (
                    <th key={c.key} style={styles.th} onClick={() => handleSort(c.key)}>
                      {c.label} {sortKey === c.key ? (sortDir === 'desc' ? '↓' : '↑') : ''}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {sorted.map((r, idx) => (
                  <tr key={r.recruiter_id} style={idx % 2 === 0 ? styles.trEven : styles.trOdd}>
                    <td style={styles.td}>
                      <div style={styles.nameCell}>
                        <div style={styles.avatar}>{r.recruiter_name?.[0] ?? '?'}</div>
                        {r.recruiter_name}
                      </div>
                    </td>
                    <td style={styles.td}>{bar(r.candidates_reviewed, maxReviewed, '#6c63ff')}</td>
                    <td style={styles.td}>{bar(r.interviews_scheduled, maxInterviews, '#06b6d4')}</td>
                    <td style={styles.td}>{bar(r.hires_made, maxHires, '#10b981')}</td>
                    <td style={styles.td}>
                      <span style={{ color: r.scorecard_completion_rate >= 80 ? '#10b981' : '#f59e0b', fontWeight: 600 }}>
                        {r.scorecard_completion_rate.toFixed(1)}%
                      </span>
                    </td>
                    <td style={styles.td}>
                      <span style={{ color: r.sla_compliance_rate >= 90 ? '#10b981' : r.sla_compliance_rate >= 70 ? '#f59e0b' : '#ef4444', fontWeight: 600 }}>
                        {r.sla_compliance_rate.toFixed(1)}%
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  page: { minHeight: '100vh', background: '#0f1117', color: '#e0e0e0', fontFamily: "'Inter', sans-serif", padding: '32px' },
  header: { marginBottom: 32 },
  title: { fontSize: 28, fontWeight: 800, margin: 0, background: 'linear-gradient(135deg, #6c63ff, #8e85ff)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' },
  subtitle: { color: '#888', fontSize: 14, marginTop: 4 },
  loadingPulse: { color: '#888', fontSize: 15, textAlign: 'center', paddingTop: 80 },
  empty: { color: '#666', fontSize: 15, textAlign: 'center', paddingTop: 80 },
  leaderGrid: { display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16, marginBottom: 24 },
  leaderCard: { background: '#1a1d2e', borderRadius: 16, padding: 24, textAlign: 'center' },
  medal: { fontSize: 36, marginBottom: 8 },
  leaderName: { fontSize: 16, fontWeight: 700, marginBottom: 4 },
  leaderStat: { fontSize: 13, color: '#6c63ff', fontWeight: 600, marginBottom: 8 },
  leaderMini: { display: 'flex', justifyContent: 'center', gap: 16, fontSize: 12, color: '#888' },
  tableCard: { background: '#1a1d2e', borderRadius: 16, overflow: 'hidden', border: '1px solid #2d3250' },
  table: { width: '100%', borderCollapse: 'collapse', fontSize: 13 },
  th: { padding: '12px 16px', textAlign: 'left', color: '#888', fontWeight: 600, borderBottom: '1px solid #2d3250', cursor: 'pointer', userSelect: 'none', fontSize: 12, textTransform: 'uppercase', letterSpacing: 0.5 },
  trEven: { background: '#1a1d2e' },
  trOdd: { background: '#1e2132' },
  td: { padding: '12px 16px', borderBottom: '1px solid #1a1d2e' },
  nameCell: { display: 'flex', alignItems: 'center', gap: 10 },
  avatar: { width: 32, height: 32, borderRadius: '50%', background: 'linear-gradient(135deg, #6c63ff, #8e85ff)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700, fontSize: 13, color: '#fff' },
}
