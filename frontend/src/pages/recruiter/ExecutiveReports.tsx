import { useState } from 'react'
import { api } from '../../api'

const REPORT_TYPES = [
  { value: 'pipeline', label: '📋 Pipeline Report', desc: 'All applications with status, source, and timestamps' },
  { value: 'recruiter', label: '👤 Recruiter Report', desc: 'Recruiter productivity and SLA metrics' },
  { value: 'candidate', label: '🙋 Candidate Report', desc: 'Application breakdown by source and status' },
  { value: 'offer', label: '💼 Offer Report', desc: 'Offer acceptance rates and pending offers' },
  { value: 'velocity', label: '⚡ Velocity Report', desc: 'Time-to-hire trend over recent periods' },
  { value: 'executive_summary', label: '🏆 Executive Summary', desc: 'Full KPI summary for leadership review' },
]

const FORMATS = [
  { value: 'CSV', label: '📄 CSV', desc: 'Lightweight, spreadsheet compatible' },
  { value: 'XLSX', label: '📊 Excel', desc: 'Native .xlsx with branding' },
  { value: 'PDF', label: '📑 PDF', desc: 'Branded report with KPI cards' },
]

interface ReportJob {
  report_id: string
  status: string
  format: string
  expires_at: string
}

export default function ExecutiveReports() {
  const [reportType, setReportType] = useState('executive_summary')
  const [format, setFormat] = useState('PDF')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [department, setDepartment] = useState('')
  const [source, setSource] = useState('')
  const [includeArchived, setIncludeArchived] = useState(false)
  const [windowDays, setWindowDays] = useState(90)
  const [submitting, setSubmitting] = useState(false)
  const [jobs, setJobs] = useState<ReportJob[]>([])
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  const handleExport = async () => {
    setSubmitting(true)
    setError(null)
    setSuccess(null)
    try {
      const body: Record<string, any> = {
        report_type: reportType,
        format,
        include_archived: includeArchived,
        window_days: windowDays,
      }
      if (dateFrom) body.date_from = new Date(dateFrom).toISOString()
      if (dateTo) body.date_to = new Date(dateTo).toISOString()
      if (department) body.department = department
      if (source) body.source = source

      const r = await api.post('/v1/executive/reports/export', body)
      const d = r.data
      setJobs(prev => [d, ...prev])
      setSuccess(`Report queued (ID: ${d.report_id.slice(0, 8)}…). Ready to download once status is COMPLETED.`)
      pollStatus(d.report_id)
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Export failed')
    } finally {
      setSubmitting(false)
    }
  }

  const pollStatus = (reportId: string) => {
    const interval = setInterval(async () => {
      try {
        const r = await api.get(`/v1/executive/reports/${reportId}`)
        const d = r.data
        setJobs(prev => prev.map(j => j.report_id === reportId ? { ...j, status: d.status } : j))
        if (d.status === 'COMPLETED' || d.status === 'FAILED' || d.status === 'EXPIRED') {
          clearInterval(interval)
        }
      } catch {
        clearInterval(interval)
      }
    }, 2500)
  }

  const handleDownload = async (reportId: string) => {
    try {
      const r = await api.get(`/v1/executive/reports/${reportId}/download`, { responseType: 'blob' })
      const job = jobs.find(j => j.report_id === reportId)
      const ext = job?.format?.toLowerCase() || 'pdf'
      const url = URL.createObjectURL(new Blob([r.data]))
      const a = document.createElement('a')
      a.href = url
      a.download = `executive-report-${reportId.slice(0, 8)}.${ext}`
      a.click()
      URL.revokeObjectURL(url)
    } catch { /* ignore */ }
  }

  const statusColor = (s: string) => {
    if (s === 'COMPLETED') return '#10b981'
    if (s === 'FAILED') return '#ef4444'
    if (s === 'EXPIRED') return '#666'
    return '#f59e0b'
  }

  return (
    <div style={styles.page}>
      <div style={styles.header}>
        <div>
          <h1 style={styles.title}>Export Reports</h1>
          <p style={styles.subtitle}>Generate branded CSV, Excel, and PDF reports for leadership and compliance</p>
        </div>
      </div>

      <div style={styles.layout}>
        {/* Configuration Panel */}
        <div style={styles.configPanel}>
          <div style={styles.section}>
            <div style={styles.sectionTitle}>Report Type</div>
            <div style={styles.typeGrid}>
              {REPORT_TYPES.map(rt => (
                <button
                  key={rt.value}
                  id={`exec-rtype-${rt.value}`}
                  style={{ ...styles.typeBtn, ...(reportType === rt.value ? styles.typeBtnActive : {}) }}
                  onClick={() => setReportType(rt.value)}
                >
                  <div style={styles.typeBtnLabel}>{rt.label}</div>
                  <div style={styles.typeBtnDesc}>{rt.desc}</div>
                </button>
              ))}
            </div>
          </div>

          <div style={styles.section}>
            <div style={styles.sectionTitle}>Output Format</div>
            <div style={styles.fmtRow}>
              {FORMATS.map(f => (
                <button
                  key={f.value}
                  id={`exec-fmt-${f.value}`}
                  style={{ ...styles.fmtBtn, ...(format === f.value ? styles.fmtBtnActive : {}) }}
                  onClick={() => setFormat(f.value)}
                >
                  <div style={styles.fmtLabel}>{f.label}</div>
                  <div style={styles.fmtDesc}>{f.desc}</div>
                </button>
              ))}
            </div>
          </div>

          <div style={styles.section}>
            <div style={styles.sectionTitle}>Filters</div>
            <div style={styles.filtersGrid}>
              <div style={styles.fieldGroup}>
                <label style={styles.fieldLabel}>Date From</label>
                <input id="exec-filter-date-from" type="date" style={styles.input} value={dateFrom} onChange={e => setDateFrom(e.target.value)} />
              </div>
              <div style={styles.fieldGroup}>
                <label style={styles.fieldLabel}>Date To</label>
                <input id="exec-filter-date-to" type="date" style={styles.input} value={dateTo} onChange={e => setDateTo(e.target.value)} />
              </div>
              <div style={styles.fieldGroup}>
                <label style={styles.fieldLabel}>Department</label>
                <input id="exec-filter-dept" type="text" placeholder="e.g. Engineering" style={styles.input} value={department} onChange={e => setDepartment(e.target.value)} />
              </div>
              <div style={styles.fieldGroup}>
                <label style={styles.fieldLabel}>Source Channel</label>
                <select id="exec-filter-source" style={styles.input} value={source} onChange={e => setSource(e.target.value)}>
                  <option value="">All Sources</option>
                  {['LinkedIn', 'Careers Page', 'Referral', 'Indeed', 'Naukri', 'Manual Upload', 'Agency', 'Campus'].map(s => (
                    <option key={s} value={s}>{s}</option>
                  ))}
                </select>
              </div>
              <div style={styles.fieldGroup}>
                <label style={styles.fieldLabel}>Forecast Window</label>
                <select id="exec-filter-window" style={styles.input} value={windowDays} onChange={e => setWindowDays(Number(e.target.value))}>
                  {[30, 60, 90].map(d => <option key={d} value={d}>{d} days</option>)}
                </select>
              </div>
              <div style={{ ...styles.fieldGroup, justifyContent: 'flex-end', paddingTop: 24 }}>
                <label style={{ ...styles.fieldLabel, display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
                  <input id="exec-filter-archived" type="checkbox" checked={includeArchived} onChange={e => setIncludeArchived(e.target.checked)} style={{ accentColor: '#6c63ff' }} />
                  Include Archived
                </label>
              </div>
            </div>
          </div>

          {error && <div style={styles.errorBox}>{error}</div>}
          {success && <div style={styles.successBox}>{success}</div>}

          <button id="exec-export-btn" style={styles.exportBtn} onClick={handleExport} disabled={submitting}>
            {submitting ? '⏳ Generating…' : `📥 Export ${format} Report`}
          </button>
        </div>

        {/* Jobs Panel */}
        <div style={styles.jobsPanel}>
          <div style={styles.sectionTitle}>Recent Exports</div>
          {jobs.length === 0 ? (
            <p style={styles.noJobs}>No exports yet. Configure and generate a report to get started.</p>
          ) : (
            jobs.map(job => (
              <div key={job.report_id} style={styles.jobCard}>
                <div style={styles.jobHeader}>
                  <span style={styles.jobId}>{job.report_id.slice(0, 12)}…</span>
                  <span style={{ ...styles.jobStatus, color: statusColor(job.status) }}>{job.status}</span>
                </div>
                <div style={styles.jobMeta}>
                  Format: <strong>{job.format}</strong> · Expires: {new Date(job.expires_at).toLocaleDateString()}
                </div>
                {job.status === 'COMPLETED' && (
                  <button
                    id={`exec-download-${job.report_id}`}
                    style={styles.downloadBtn}
                    onClick={() => handleDownload(job.report_id)}
                  >
                    ⬇ Download
                  </button>
                )}
                {(job.status === 'PENDING' || job.status === 'PROCESSING') && (
                  <div style={styles.processingNote}>⏳ Generating… please wait</div>
                )}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  page: { minHeight: '100vh', background: '#0f1117', color: '#e0e0e0', fontFamily: "'Inter', sans-serif", padding: '32px' },
  header: { marginBottom: 32 },
  title: { fontSize: 28, fontWeight: 800, margin: 0, background: 'linear-gradient(135deg, #6c63ff, #8e85ff)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' },
  subtitle: { color: '#888', fontSize: 14, marginTop: 4 },
  layout: { display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 24, alignItems: 'start' },
  configPanel: { background: '#1a1d2e', borderRadius: 16, padding: 28, border: '1px solid #2d3250' },
  jobsPanel: { background: '#1a1d2e', borderRadius: 16, padding: 24, border: '1px solid #2d3250' },
  section: { marginBottom: 28 },
  sectionTitle: { fontSize: 13, fontWeight: 700, color: '#888', textTransform: 'uppercase', letterSpacing: 0.8, marginBottom: 12 },
  typeGrid: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 },
  typeBtn: { background: '#0f1117', border: '1px solid #2d3250', borderRadius: 12, padding: '12px 14px', cursor: 'pointer', textAlign: 'left', transition: 'all 0.2s' },
  typeBtnActive: { border: '1px solid #6c63ff', background: 'rgba(108,99,255,0.12)' },
  typeBtnLabel: { fontSize: 14, fontWeight: 600, color: '#e0e0e0', marginBottom: 4 },
  typeBtnDesc: { fontSize: 11, color: '#666' },
  fmtRow: { display: 'flex', gap: 12 },
  fmtBtn: { flex: 1, background: '#0f1117', border: '1px solid #2d3250', borderRadius: 12, padding: '12px 10px', cursor: 'pointer', textAlign: 'center', transition: 'all 0.2s' },
  fmtBtnActive: { border: '1px solid #6c63ff', background: 'rgba(108,99,255,0.12)' },
  fmtLabel: { fontSize: 15, fontWeight: 700, color: '#e0e0e0', marginBottom: 4 },
  fmtDesc: { fontSize: 11, color: '#666' },
  filtersGrid: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 },
  fieldGroup: { display: 'flex', flexDirection: 'column', gap: 4 },
  fieldLabel: { fontSize: 12, color: '#888', fontWeight: 600 },
  input: { background: '#0f1117', border: '1px solid #2d3250', borderRadius: 8, padding: '8px 12px', color: '#e0e0e0', fontSize: 13, outline: 'none' },
  errorBox: { background: 'rgba(239,68,68,0.12)', border: '1px solid rgba(239,68,68,0.3)', borderRadius: 10, padding: '12px 16px', color: '#ef4444', fontSize: 13, marginBottom: 16 },
  successBox: { background: 'rgba(16,185,129,0.12)', border: '1px solid rgba(16,185,129,0.3)', borderRadius: 10, padding: '12px 16px', color: '#10b981', fontSize: 13, marginBottom: 16 },
  exportBtn: { width: '100%', padding: '14px', borderRadius: 12, border: 'none', background: 'linear-gradient(135deg, #6c63ff, #8e85ff)', color: '#fff', cursor: 'pointer', fontWeight: 700, fontSize: 15 },
  noJobs: { color: '#666', fontSize: 13, lineHeight: 1.6 },
  jobCard: { background: '#0f1117', borderRadius: 12, padding: '16px', border: '1px solid #2d3250', marginBottom: 12 },
  jobHeader: { display: 'flex', justifyContent: 'space-between', marginBottom: 6 },
  jobId: { fontSize: 12, color: '#888', fontFamily: 'monospace' },
  jobStatus: { fontSize: 12, fontWeight: 700 },
  jobMeta: { fontSize: 12, color: '#666', marginBottom: 10 },
  downloadBtn: { width: '100%', padding: '8px', borderRadius: 8, border: '1px solid #6c63ff', background: 'rgba(108,99,255,0.1)', color: '#8e85ff', cursor: 'pointer', fontWeight: 600, fontSize: 13 },
  processingNote: { fontSize: 12, color: '#f59e0b', textAlign: 'center' },
}
