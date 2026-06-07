import { useEffect, useMemo } from 'react'
import AppLayout from '../components/AppLayout'
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell
} from 'recharts'
import { fetchSyncMetrics } from '../api'

export default function AnalyticsDashboard() {
  useEffect(() => {
    fetchSyncMetrics().catch(() => {})
  }, [])

  // SmartOnboard design tokens colors for charts
  const chartColors = useMemo(() => {
    return {
      primary: '#ffedd7',       // Warm Cream
      accent: '#dc5000',        // Burnt Sienna
      success: '#ffedd7',       // Warm Cream
      warning: '#6c5f51',       // Grey Brown
      danger: '#dc5000',        // Burnt Sienna
      grid: '#40372e',          // Cork Shadow
      text: '#6c5f51',          // Grey Brown
      tooltipBg: '#100904',     // Studio Black
      tooltipBorder: '#40372e'  // Cork Shadow
    }
  }, [])

  // 1. Hiring Funnel Density
  const funnelData = [
    { name: 'Applied', value: 120 },
    { name: 'Screening', value: 85 },
    { name: 'Interview', value: 42 },
    { name: 'Committee', value: 24 },
    { name: 'Offer', value: 12 },
    { name: 'Hired', value: 8 }
  ]

  // 2. Stage Velocity (Average Days in Stage)
  const velocityData = [
    { stage: 'Screening', days: 2 },
    { stage: 'Interview', days: 6 },
    { stage: 'Committee', days: 3 },
    { stage: 'Offer', days: 4 },
    { stage: 'Pre-board', days: 5 }
  ]

  // 3. Offer Acceptance Rates (Monthly)
  const offerAcceptanceData = [
    { month: 'Jan', rate: 75 },
    { month: 'Feb', rate: 82 },
    { month: 'Mar', rate: 80 },
    { month: 'Apr', rate: 88 },
    { month: 'May', rate: 92 },
    { month: 'Jun', rate: 90 }
  ]

  // 4. Pre-boarding Onboarding Completion Rates
  const onboardingCompletionData = [
    { name: 'Completed Checklists', value: 72 },
    { name: 'Overdue Checklist Tasks', value: 18 },
    { name: 'Active Escalation Breaches', value: 10 }
  ]
  const PIE_COLORS = [chartColors.primary, chartColors.warning, chartColors.accent]

  return (
    <AppLayout>
      <div className="dashboard-page container container--wide" style={{ paddingBottom: 'var(--space-12)' }}>
        
        {/* Title Header */}
        <header style={{ marginBottom: 'var(--space-8)' }}>
          <h1 style={{ fontSize: '29px', fontWeight: 500, letterSpacing: '-0.02em', marginBottom: '4px', lineHeight: 1.09, color: 'var(--text)' }}>
            Executive Visibility Analytics
          </h1>
          <p className="text-secondary" style={{ fontSize: '14px', lineHeight: 1.33 }}>
            Expose pre-boarding velocities, funnels yield, and HRIS outbox sweeps quotas in curated SmartOnboard style.
          </p>
        </header>

        {/* TOP METRIC CARDS ROW */}
        <section
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
            gap: 'var(--space-4)',
            marginBottom: 'var(--space-8)'
          }}
          aria-label="Executive Metrics"
        >
          {[
            { label: 'Total Candidates Processed', value: 120, pct: '+12% vs last month' },
            { label: 'Total Pre-boarding Hires', value: 8, pct: '100% conversion rate' },
            { label: 'Active Employees Directory', value: 3, pct: 'Gusto / BambooHR sync active' },
            { label: 'Failed Outbox Sweeps (DLQ)', value: 0, pct: 'Outbox processors healthy' }
          ].map((card, idx) => (
            <div key={idx} className="card" style={{ padding: 'var(--space-5)', border: '1px dashed var(--color-cork-shadow)', borderRadius: '12px', background: 'transparent', boxShadow: 'none' }}>
              <span style={{ fontSize: '10px', fontWeight: 500, color: 'var(--color-grey-brown)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{card.label}</span>
              <strong style={{ fontSize: '29px', fontWeight: 500, color: 'var(--text)', display: 'block', marginTop: '4px' }}>{card.value}</strong>
              <span style={{ fontSize: '10px', color: 'var(--color-grey-brown)', display: 'block', marginTop: '6px' }}>{card.pct}</span>
            </div>
          ))}
        </section>

        {/* RECHARTS GRAPHS GRID PANEL */}
        <section
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(440px, 1fr))',
            gap: 'var(--space-6)'
          }}
          aria-label="Analytics Visualizations"
        >
          {/* Graph 1: Hiring Funnel Conversion (Bar Chart) */}
          <div className="card" style={{ padding: 'var(--space-5)', borderRadius: '12px', border: '1px dashed var(--color-cork-shadow)', background: 'transparent' }}>
            <h3 style={{ fontSize: '14px', fontWeight: 500, color: 'var(--text)', marginBottom: 'var(--space-4)' }}>Hiring Funnel Yield (Applicant Density)</h3>
            <div style={{ width: '100%', height: '260px' }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={funnelData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke={chartColors.grid} />
                  <XAxis dataKey="name" stroke={chartColors.text} style={{ fontSize: '10px' }} />
                  <YAxis stroke={chartColors.text} style={{ fontSize: '10px' }} />
                  <Tooltip contentStyle={{ background: chartColors.tooltipBg, borderColor: chartColors.tooltipBorder, borderRadius: '0px', fontSize: '11px' }} />
                  <Bar dataKey="value" fill={chartColors.primary} radius={[0, 0, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Graph 2: Stage Velocity - Average Days (Area Chart) */}
          <div className="card" style={{ padding: 'var(--space-5)', borderRadius: '12px', border: '1px dashed var(--color-cork-shadow)', background: 'transparent' }}>
            <h3 style={{ fontSize: '14px', fontWeight: 500, color: 'var(--text)', marginBottom: 'var(--space-4)' }}>Average Days In Hiring Stage (Velocity)</h3>
            <div style={{ width: '100%', height: '260px' }}>
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={velocityData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke={chartColors.grid} />
                  <XAxis dataKey="stage" stroke={chartColors.text} style={{ fontSize: '10px' }} />
                  <YAxis stroke={chartColors.text} style={{ fontSize: '10px' }} />
                  <Tooltip contentStyle={{ background: chartColors.tooltipBg, borderColor: chartColors.tooltipBorder, borderRadius: '0px', fontSize: '11px' }} />
                  <Area type="monotone" dataKey="days" stroke={chartColors.accent} fill={chartColors.accent} fillOpacity={0.15} strokeWidth={1} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Graph 3: Offer Acceptance Yield (Line Chart) */}
          <div className="card" style={{ padding: 'var(--space-5)', borderRadius: '12px', border: '1px dashed var(--color-cork-shadow)', background: 'transparent' }}>
            <h3 style={{ fontSize: '14px', fontWeight: 500, color: 'var(--text)', marginBottom: 'var(--space-4)' }}>Offer Acceptance Rate Percentage (Yield)</h3>
            <div style={{ width: '100%', height: '260px' }}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={offerAcceptanceData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke={chartColors.grid} />
                  <XAxis dataKey="month" stroke={chartColors.text} style={{ fontSize: '10px' }} />
                  <YAxis stroke={chartColors.text} style={{ fontSize: '10px' }} unit="%" />
                  <Tooltip contentStyle={{ background: chartColors.tooltipBg, borderColor: chartColors.tooltipBorder, borderRadius: '0px', fontSize: '11px' }} />
                  <Line type="monotone" dataKey="rate" stroke={chartColors.accent} strokeWidth={2} dot={{ r: 3 }} activeDot={{ r: 5 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Graph 4: Onboarding Completion Distribution (Pie Chart) */}
          <div className="card" style={{ padding: 'var(--space-5)', borderRadius: '12px', border: '1px dashed var(--color-cork-shadow)', background: 'transparent' }}>
            <h3 style={{ fontSize: '14px', fontWeight: 500, color: 'var(--text)', marginBottom: 'var(--space-4)' }}>Onboarding Checklist Distribution</h3>
            <div style={{ width: '100%', height: '260px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <div style={{ width: '50%', height: '100%' }}>
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={onboardingCompletionData}
                      cx="50%"
                      cy="50%"
                      innerRadius={50}
                      outerRadius={75}
                      paddingAngle={4}
                      dataKey="value"
                    >
                      {onboardingCompletionData.map((_, index) => (
                        <Cell key={`cell-${index}`} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip contentStyle={{ background: chartColors.tooltipBg, borderColor: chartColors.tooltipBorder, borderRadius: '0px', fontSize: '11px' }} />
                  </PieChart>
                </ResponsiveContainer>
              </div>

              {/* Legends */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', width: '50%', fontSize: '11px', fontWeight: 500 }}>
                {onboardingCompletionData.map((d, idx) => (
                  <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span style={{ width: '10px', height: '10px', borderRadius: '0px', background: PIE_COLORS[idx] }} />
                    <span style={{ color: 'var(--color-grey-brown)' }}>{d.name}: <strong style={{ color: 'var(--text)', fontWeight: 500 }}>{d.value}%</strong></span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

      </div>
    </AppLayout>
  )
}
