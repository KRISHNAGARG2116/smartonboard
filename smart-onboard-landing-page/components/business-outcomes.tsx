'use client'

import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  Cell,
  ResponsiveContainer,
  XAxis,
} from 'recharts'
import { SectionLabel } from '@/components/primitives'
import { Reveal } from '@/components/reveal'

const VELOCITY = [
  { m: 'Jan', v: 22 },
  { m: 'Feb', v: 20 },
  { m: 'Mar', v: 18 },
  { m: 'Apr', v: 16 },
  { m: 'May', v: 13 },
  { m: 'Jun', v: 11 },
]

const FUNNEL = [
  { stage: 'Applied', v: 100 },
  { stage: 'Screened', v: 74 },
  { stage: 'Interview', v: 38 },
  { stage: 'Offer', v: 16 },
  { stage: 'Hired', v: 12 },
]

const TILES = [
  { label: 'Acceptance rate', value: '92%', trend: '+14 pts', up: true },
  { label: 'AI screening accuracy', value: '98.4%', trend: 'vs. human review', up: true },
  { label: 'Recruiter efficiency', value: '3.2×', trend: 'roles per recruiter', up: true },
  { label: 'Cost per hire', value: '−41%', trend: 'year over year', up: true },
]

export function BusinessOutcomes() {
  return (
    <section id="outcomes" className="bg-foreground text-background">
      <div className="mx-auto max-w-6xl px-6 py-20 md:py-28">
        <Reveal className="max-w-2xl">
          <SectionLabel className="text-background/60 [&>span]:bg-background/25">
            Business outcomes
          </SectionLabel>
          <h2 className="mt-5 text-balance font-heading text-4xl leading-tight text-background md:text-5xl">
            The numbers leadership actually asks about.
          </h2>
          <p className="mt-4 max-w-xl text-pretty text-[16px] leading-relaxed text-background/65">
            Every action in SmartOnboard rolls up into a single executive view —
            faster hiring, higher acceptance, and a pipeline you can forecast.
          </p>
        </Reveal>

        <Reveal delay={0.1} className="mt-12 grid grid-cols-1 gap-4 lg:grid-cols-[1.4fr_1fr]">
          {/* Velocity chart */}
          <div className="rounded-[24px] border border-background/12 bg-background/[0.04] p-6">
            <div className="flex items-end justify-between">
              <div>
                <p className="text-[13px] text-background/60">Average time to hire</p>
                <p className="mt-1 font-heading text-5xl leading-none text-background">
                  11 <span className="text-[18px] text-background/55">days</span>
                </p>
              </div>
              <span className="rounded-full bg-success/20 px-3 py-1 text-[12.5px] font-semibold text-[oklch(0.86_0.12_155)]">
                ↓ 50% in 6 months
              </span>
            </div>
            <div className="mt-6 h-44">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={VELOCITY} margin={{ top: 6, right: 6, left: 6, bottom: 0 }}>
                  <defs>
                    <linearGradient id="vel" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="oklch(0.98 0 0)" stopOpacity={0.35} />
                      <stop offset="100%" stopColor="oklch(0.98 0 0)" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <XAxis
                    dataKey="m"
                    tickLine={false}
                    axisLine={false}
                    tick={{ fill: 'oklch(0.98 0 0 / 0.5)', fontSize: 11 }}
                    dy={6}
                  />
                  <Area
                    type="monotone"
                    dataKey="v"
                    stroke="oklch(0.98 0 0)"
                    strokeWidth={2.5}
                    fill="url(#vel)"
                    dot={{ r: 3, fill: 'oklch(0.98 0 0)' }}
                    activeDot={{ r: 4 }}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Funnel chart */}
          <div className="rounded-[24px] border border-background/12 bg-background/[0.04] p-6">
            <p className="text-[13px] text-background/60">Pipeline conversion</p>
            <p className="mt-1 font-heading text-3xl leading-none text-background">12% applied → hired</p>
            <div className="mt-5 h-44">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={FUNNEL} margin={{ top: 4, right: 0, left: 0, bottom: 0 }}>
                  <XAxis
                    dataKey="stage"
                    tickLine={false}
                    axisLine={false}
                    tick={{ fill: 'oklch(0.98 0 0 / 0.5)', fontSize: 10 }}
                    interval={0}
                    dy={6}
                  />
                  <Bar dataKey="v" radius={[6, 6, 6, 6]} barSize={26}>
                    {FUNNEL.map((entry, i) => (
                      <Cell
                        key={i}
                        fill={
                          i === FUNNEL.length - 1
                            ? 'oklch(0.7 0.13 155)'
                            : `oklch(0.98 0 0 / ${0.85 - i * 0.13})`
                        }
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </Reveal>

        <Reveal delay={0.15} className="mt-4 grid grid-cols-2 gap-4 lg:grid-cols-4">
          {TILES.map((t) => (
            <div key={t.label} className="rounded-[20px] border border-background/12 bg-background/[0.04] p-5">
              <p className="text-[12px] text-background/55">{t.label}</p>
              <p className="mt-2 font-heading text-4xl leading-none text-background">{t.value}</p>
              <p className="mt-2 text-[11.5px] text-background/50">{t.trend}</p>
            </div>
          ))}
        </Reveal>
      </div>
    </section>
  )
}
