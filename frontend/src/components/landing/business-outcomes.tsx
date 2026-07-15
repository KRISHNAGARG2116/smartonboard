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
  { label: 'AI accuracy', value: '98.4%', trend: 'vs. human review', up: true },
  { label: 'Efficiency', value: '3.2×', trend: 'roles/recruiter', up: true },
  { label: 'Cost/hire', value: '−41%', trend: 'year over year', up: true },
]

export function BusinessOutcomes() {
  return (
    <section className="relative mx-auto w-full px-6 py-10 md:py-14">
      <div className="mx-auto w-full grid grid-cols-1 lg:grid-cols-[1.9fr_1.1fr] gap-8 items-center">
        {/* Left Column: Outcomes content (Charts & Tiles) - Visual-First! */}
        <div className="order-2 lg:order-1">
          <Reveal delay={0.1} className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            {/* Velocity chart */}
            <div className="rounded-[24px] border border-[#e4d9ce] bg-white p-5 shadow-soft">
              <div className="flex items-end justify-between">
                <div>
                  <p className="text-[13px] text-zinc-500 font-semibold">Average time to hire</p>
                  <p className="mt-1 font-heading text-4xl leading-none text-[#1f090b]">
                    11 <span className="text-[16px] text-zinc-500 font-semibold">days</span>
                  </p>
                </div>
                <span className="rounded-full bg-[#3c5e43]/12 px-2.5 py-0.5 text-[11.5px] font-semibold text-[#3c5e43]">
                  ↓ 50%
                </span>
              </div>
              <div className="mt-3 h-36">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={VELOCITY} margin={{ top: 6, right: 6, left: 6, bottom: 0 }}>
                    <defs>
                      <linearGradient id="vel" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#4a1f2c" stopOpacity={0.2} />
                        <stop offset="100%" stopColor="#4a1f2c" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <XAxis
                      dataKey="m"
                      tickLine={false}
                      axisLine={false}
                      tick={{ fill: '#5c4a43', fontSize: 10 }}
                      dy={4}
                    />
                    <Area
                      type="monotone"
                      dataKey="v"
                      stroke="#4a1f2c"
                      strokeWidth={2.5}
                      fill="url(#vel)"
                      dot={{ r: 3, fill: '#4a1f2c' }}
                      activeDot={{ r: 4 }}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Funnel chart */}
            <div className="rounded-[24px] border border-[#e4d9ce] bg-white p-5 shadow-soft">
              <p className="text-[13px] text-zinc-500 font-semibold">Pipeline conversion</p>
              <p className="mt-1 font-heading text-2xl leading-none text-[#1f090b]">12% applied → hired</p>
              <div className="mt-3 h-36">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={FUNNEL} margin={{ top: 4, right: 0, left: 0, bottom: 0 }}>
                    <XAxis
                      dataKey="stage"
                      tickLine={false}
                      axisLine={false}
                      tick={{ fill: '#5c4a43', fontSize: 9 }}
                      interval={0}
                      dy={4}
                    />
                    <Bar dataKey="v" radius={[6, 6, 6, 6]} barSize={22}>
                      {FUNNEL.map((_, i) => (
                        <Cell
                          key={i}
                          fill={
                            i === FUNNEL.length - 1
                              ? '#3c5e43'
                              : `rgba(74, 31, 44, ${0.85 - i * 0.15})`
                          }
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </Reveal>

          <Reveal delay={0.15} className="mt-4 grid grid-cols-2 gap-3 lg:grid-cols-4">
            {TILES.map((t) => (
              <div key={t.label} className="rounded-[18px] border border-[#e4d9ce] bg-white p-4 shadow-soft">
                <p className="text-[11.5px] text-zinc-500 font-semibold">{t.label}</p>
                <p className="mt-1.5 font-heading text-3xl leading-none text-[#1f090b]">{t.value}</p>
                <p className="mt-1 text-[10.5px] text-zinc-500 font-medium">{t.trend}</p>
              </div>
            ))}
          </Reveal>
        </div>

        {/* Right Column: Heading and Text */}
        <Reveal className="max-w-xl order-1 lg:order-2">
          <SectionLabel>
            Business outcomes
          </SectionLabel>
          <h2 className="mt-3 text-balance font-heading text-4xl leading-tight text-[#1f090b] md:text-5xl">
            The numbers leadership actually asks about.
          </h2>
          <p className="mt-3 text-pretty text-[16px] leading-relaxed text-zinc-600 font-medium">
            Every action in SmartOnboard rolls up into a single executive view —
            faster hiring, higher acceptance, and a pipeline you can forecast.
          </p>
        </Reveal>
      </div>
    </section>
  )
}
