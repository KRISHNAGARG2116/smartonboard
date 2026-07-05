import { useState, useEffect } from 'react'
import { api } from '../../api'

export default function ExecutiveForecast() {
  const [windowDays, setWindowDays] = useState(90)
  const [forecast, setForecast] = useState<any | null>(null)
  const [loading, setLoading] = useState(false)
  const [aiSummary, setAiSummary] = useState<string | null>(null)
  const [aiLoading, setAiLoading] = useState(false)
  const [aiError, setAiError] = useState<string | null>(null)

  const fetchForecast = async (days: number) => {
    setLoading(true)
    try {
      const r = await api.get(`/v1/executive/forecast?window_days=${days}`)
      setForecast(r.data)
    } catch { /* swallow */ } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchForecast(windowDays) }, [windowDays])

  const handleAISummary = async () => {
    setAiLoading(true)
    setAiError(null)
    try {
      const r = await api.post('/v1/executive/ai-summary', { window_days: windowDays })
      setAiSummary(r.data.summary)
    } catch {
      setAiError('Failed to generate AI summary.')
    } finally {
      setAiLoading(false)
    }
  }

  const confidenceColor = (c?: string) => {
    if (c === 'Medium') return '#f59e0b'
    if (c === 'Low') return '#ef4444'
    return '#10b981'
  }

  const fc = forecast?.forecast
  const ex = forecast?.explanation

  return (
    <div style={styles.page}>
      <div style={styles.header}>
        <div>
          <h1 style={styles.title}>Hiring Forecast</h1>
          <p style={styles.subtitle}>Deterministic projections based on rolling historical averages</p>
        </div>

        {/* Window selector */}
        <div style={styles.windowSelector}>
          {[30, 60, 90].map(d => (
            <button
              key={d}
              id={`exec-window-${d}`}
              style={{ ...styles.windowBtn, ...(windowDays === d ? styles.windowBtnActive : {}) }}
              onClick={() => setWindowDays(d)}
            >
              {d}d
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div style={styles.loadingPulse}>Calculating forecast…</div>
      ) : forecast && (
        <>
          {/* Forecast Cards */}
          <div style={styles.forecastGrid}>
            {[
              { label: 'Expected Hires', value: fc?.expected_hires, icon: '👥', unit: '' },
              { label: 'Recruiter Capacity', value: fc?.recruiter_capacity, icon: '⚡', unit: '' },
              { label: 'Exp. Time to Fill', value: fc?.expected_time_to_fill_days, icon: '📅', unit: 'days' },
              { label: 'Hiring Target %', value: fc?.hiring_target_completion_pct, icon: '🎯', unit: '%' },
            ].map(card => (
              <div key={card.label} style={styles.forecastCard}>
                <span style={styles.forecastIcon}>{card.icon}</span>
                <div style={styles.forecastVal}>{card.value}{card.unit}</div>
                <div style={styles.forecastLbl}>{card.label}</div>
              </div>
            ))}
          </div>

          {/* Explanation Panel */}
          <div style={styles.explanationPanel}>
            <div style={styles.panelHeader}>
              <span style={styles.panelTitle}>📊 Forecast Explanation</span>
              <span style={{ ...styles.confidenceBadge, color: confidenceColor(ex?.confidence) }}>
                {ex?.confidence} Confidence
              </span>
            </div>
            <div style={styles.explanationGrid}>
              {[
                { label: 'Analysis Window', value: ex?.window_used },
                { label: 'Historical Average', value: `${ex?.historical_average} hires/month` },
                { label: 'Active Requisitions', value: ex?.active_requisitions },
                { label: 'Recruiter Capacity', value: ex?.recruiter_capacity },
              ].map(item => (
                <div key={item.label} style={styles.explainItem}>
                  <div style={styles.explainLabel}>{item.label}</div>
                  <div style={styles.explainValue}>{item.value}</div>
                </div>
              ))}
            </div>
            <div style={styles.methodologyNote}>
              <strong>Methodology:</strong> This forecast is purely deterministic — no AI is used for numerical projections.
              It uses rolling historical hire velocity over the selected window combined with current open requisition count.
              AI may optionally be used to summarise these numbers below.
            </div>
          </div>

          {/* AI Narrative Summary */}
          <div style={styles.aiPanel}>
            <div style={styles.panelHeader}>
              <span style={styles.panelTitle}>🤖 AI Executive Briefing</span>
              <button
                id="exec-gen-ai-summary"
                style={styles.btnPrimary}
                onClick={handleAISummary}
                disabled={aiLoading}
              >
                {aiLoading ? 'Generating…' : aiSummary ? 'Regenerate' : 'Generate Summary'}
              </button>
            </div>
            {aiError && <div style={styles.aiError}>{aiError}</div>}
            {!aiSummary && !aiLoading && (
              <p style={styles.aiPlaceholder}>
                Click "Generate Summary" to produce an AI-written executive briefing based only on the aggregated metrics above.
                No candidate names, resumes, or scores are shared with the AI.
              </p>
            )}
            {aiLoading && <div style={styles.aiLoadingRow}>
              <div style={styles.aiDot} /><div style={{ ...styles.aiDot, animationDelay: '0.2s' }} /><div style={{ ...styles.aiDot, animationDelay: '0.4s' }} />
            </div>}
            {aiSummary && (
              <div
                style={styles.aiContent}
                dangerouslySetInnerHTML={{ __html: aiSummary.replace(/\n/g, '<br/>').replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>') }}
              />
            )}
          </div>
        </>
      )}
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  page: { minHeight: '100vh', background: '#0f1117', color: '#e0e0e0', fontFamily: "'Inter', sans-serif", padding: '32px' },
  header: { display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 32, flexWrap: 'wrap', gap: 16 },
  title: { fontSize: 28, fontWeight: 800, margin: 0, background: 'linear-gradient(135deg, #6c63ff, #8e85ff)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' },
  subtitle: { color: '#888', fontSize: 14, marginTop: 4 },
  windowSelector: { display: 'flex', gap: 8, background: '#1a1d2e', borderRadius: 10, padding: 4, border: '1px solid #2d3250' },
  windowBtn: { padding: '8px 16px', borderRadius: 8, border: 'none', background: 'transparent', color: '#888', cursor: 'pointer', fontWeight: 600, fontSize: 14, transition: 'all 0.2s' },
  windowBtnActive: { background: '#6c63ff', color: '#fff' },
  loadingPulse: { color: '#888', fontSize: 15, textAlign: 'center', paddingTop: 80 },
  forecastGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 16, marginBottom: 24 },
  forecastCard: { background: 'linear-gradient(135deg, #1a1d2e, #1e2132)', borderRadius: 16, padding: '28px 20px', textAlign: 'center', border: '1px solid #2d3250' },
  forecastIcon: { fontSize: 32, display: 'block', marginBottom: 12 },
  forecastVal: { fontSize: 32, fontWeight: 800, color: '#8e85ff', marginBottom: 6 },
  forecastLbl: { fontSize: 13, color: '#888' },
  explanationPanel: { background: '#1a1d2e', borderRadius: 16, padding: 24, border: '1px solid #2d3250', marginBottom: 24 },
  panelHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 },
  panelTitle: { fontSize: 16, fontWeight: 700 },
  confidenceBadge: { fontWeight: 700, fontSize: 13, background: 'rgba(0,0,0,0.3)', borderRadius: 8, padding: '4px 12px' },
  explanationGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12, marginBottom: 16 },
  explainItem: { background: '#0f1117', borderRadius: 10, padding: '14px 16px' },
  explainLabel: { fontSize: 11, color: '#888', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 6 },
  explainValue: { fontSize: 16, fontWeight: 700, color: '#e0e0e0' },
  methodologyNote: { background: 'rgba(108,99,255,0.08)', borderRadius: 10, padding: '12px 16px', fontSize: 13, color: '#aaa', borderLeft: '3px solid #6c63ff' },
  aiPanel: { background: '#1a1d2e', borderRadius: 16, padding: 24, border: '1px solid #2d3250' },
  btnPrimary: { padding: '10px 20px', borderRadius: 10, border: 'none', background: '#6c63ff', color: '#fff', cursor: 'pointer', fontWeight: 600, fontSize: 14 },
  aiError: { color: '#ef4444', fontSize: 13, marginBottom: 12 },
  aiPlaceholder: { color: '#666', fontSize: 14, lineHeight: 1.6 },
  aiLoadingRow: { display: 'flex', gap: 8, justifyContent: 'center', padding: '24px 0' },
  aiDot: { width: 10, height: 10, borderRadius: '50%', background: '#6c63ff' },
  aiContent: { fontSize: 14, lineHeight: 1.8, color: '#d0d0d0', background: '#0f1117', borderRadius: 10, padding: '16px 20px', marginTop: 12 },
}
