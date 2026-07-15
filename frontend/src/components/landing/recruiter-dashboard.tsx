import { Avatar, SectionLabel, WindowChrome } from '@/components/primitives'
import { Reveal } from '@/components/reveal'

const NAV = [
  { label: 'Dashboard', active: true, icon: 'M3 12l9-9 9 9M5 10v10h14V10' },
  { label: 'Jobs', icon: 'M4 7h16v13H4zM9 7V4h6v3' },
  { label: 'Candidates', icon: 'M16 18a4 4 0 0 0-8 0M12 11a3 3 0 1 0 0-6 3 3 0 0 0 0 6' },
  { label: 'Interviews', icon: 'M7 3v4M17 3v4M4 9h16M5 5h14v16H5z' },
  { label: 'Analytics', icon: 'M4 20V10M10 20V4M16 20v-7M22 20H2' },
  { label: 'Team', icon: 'M17 20v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2M9 10a4 4 0 1 0 0-8 4 4 0 0 0 0 8' },
]

const STATS = [
  { label: 'Open roles', value: '18', trend: '+3 this week', tone: 'text-[#1f090b]' },
  { label: 'In pipeline', value: '264', trend: '+41 new', tone: 'text-[#1f090b]' },
  { label: 'Interviews today', value: '6', trend: '2 upcoming', tone: 'text-[#1f090b]' },
  { label: 'Offers out', value: '4', trend: '1 accepted', tone: 'text-[#3c5e43]' },
]

const JOBS = [
  { role: 'Senior Product Designer', loc: 'Remote · US', cands: 42, stage: 'Interviewing' },
  { role: 'Staff Frontend Engineer', loc: 'New York', cands: 67, stage: 'Screening' },
  { role: 'Growth Marketing Lead', loc: 'London', cands: 31, stage: 'Sourcing' },
  { role: 'Customer Success Manager', loc: 'Remote · EU', cands: 28, stage: 'Offer' },
]

const INTERVIEWS = [
  { time: '09:30', name: 'Marcus Lee', role: 'Frontend Engineer', tone: 'blue' as const },
  { time: '11:00', name: 'Emma Johnson', role: 'Product Designer', tone: 'green' as const },
  { time: '13:30', name: 'Priya Nair', role: 'Marketing Lead', tone: 'amber' as const },
  { time: '15:00', name: 'David Okafor', role: 'Success Manager', tone: 'rose' as const },
]

const ACTIVITY = [
  { who: 'Emma Johnson', what: 'completed identity verification', when: '4m', tone: 'green' as const },
  { who: 'AI Screener', what: 'ranked 19 new applicants for Frontend Engineer', when: '22m', tone: 'ink' as const },
  { who: 'Sarah Chen', what: 'moved Marcus Lee to Final round', when: '1h', tone: 'slate' as const },
  { who: 'David Okafor', what: 'accepted the offer for Success Manager', when: '2h', tone: 'rose' as const },
]

export function RecruiterDashboard() {
  return (
    <section className="relative mx-auto w-full px-6 py-6 md:py-8">
      <div className="grid grid-cols-1 lg:grid-cols-[1fr_2.1fr] gap-10 items-center">
        {/* Left Column: Heading & Text */}
        <Reveal className="max-w-xl lg:pr-4">
          <SectionLabel>The recruiter&apos;s morning</SectionLabel>
          <h2 className="mt-3 text-balance font-heading text-4xl leading-tight text-[#1f090b] md:text-5xl">
            One workspace that already did the hard part.
          </h2>
          <p className="mt-4 text-pretty text-[16px] leading-relaxed text-zinc-600 font-medium">
            Sarah opens SmartOnboard. Overnight, the AI screened every new
            applicant, scheduled the day&apos;s interviews and surfaced the people
            worth her time.
          </p>
        </Reveal>

        {/* Right Column: Mockup dashboard */}
        <Reveal delay={0.1} className="w-full">
          <div className="overflow-hidden rounded-[24px] border border-[#e4d9ce] bg-white shadow-float">
            <WindowChrome label="app.smartonboard.com/dashboard" />

            <div className="grid grid-cols-1 md:grid-cols-[212px_1fr]">
              {/* Sidebar */}
              <aside className="hidden flex-col gap-1 border-r border-[#e4d9ce] bg-[#fcfbf7] p-3 md:flex">
                <div className="flex items-center gap-2 px-2 py-2">
                  <span className="grid size-6 place-items-center rounded-lg bg-foreground text-background text-[11px] font-bold">
                    S
                  </span>
                  <span className="text-[13px] font-bold text-zinc-800">
                    Northwind Inc.
                  </span>
                </div>
                <nav className="mt-2 flex flex-col gap-0.5" aria-label="App">
                  {NAV.map((item) => (
                    <span
                      key={item.label}
                      className={`flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-[13px] ${
                        item.active
                          ? 'bg-white font-medium text-[#4a1f2c] shadow-soft border border-[#e4d9ce]'
                          : 'text-zinc-500 hover:text-zinc-800 transition-colors'
                      }`}
                    >
                      <svg viewBox="0 0 24 24" className="size-4" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                        <path d={item.icon} />
                      </svg>
                      {item.label}
                    </span>
                  ))}
                </nav>
                <div className="mt-auto rounded-xl bg-[#faf7f2] p-3 border border-[#e4d9ce]">
                  <p className="text-[12px] font-semibold text-zinc-700">
                    AI credits
                  </p>
                  <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-fog">
                    <span className="block h-full w-[68%] rounded-full bg-foreground" />
                  </div>
                  <p className="mt-1.5 text-[11px] text-zinc-500 font-medium">
                    6,800 of 10,000 used
                  </p>
                </div>
              </aside>

              {/* Main */}
              <div className="min-w-0 p-5 md:p-6">
                {/* Top bar */}
                <div className="flex items-center justify-between gap-4">
                  <div className="flex min-w-0 items-center gap-3">
                    <Avatar name="Sarah Chen" tone="ink" size="md" />
                    <div className="min-w-0">
                      <p className="text-[15px] font-bold text-[#1f090b]">
                        Good morning, Sarah
                      </p>
                      <p className="text-[12px] text-zinc-500 font-medium">
                        Tuesday, June 30 · 24 candidates need review
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="hidden items-center gap-2 rounded-lg border border-[#e4d9ce] bg-white px-3 py-1.5 text-[12px] text-zinc-600 sm:flex">
                      <svg viewBox="0 0 24 24" className="size-3.5" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                        <circle cx="11" cy="11" r="7" />
                        <path d="m20 20-3-3" />
                      </svg>
                      Search candidates
                    </span>
                    <span className="relative grid size-8 place-items-center rounded-lg border border-[#e4d9ce] bg-white text-muted-foreground">
                      <svg viewBox="0 0 24 24" className="size-4" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
                        <path d="M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9M13.7 21a2 2 0 0 1-3.4 0" />
                      </svg>
                      <span className="absolute -right-0.5 -top-0.5 size-2 rounded-full bg-success ring-2 ring-card" />
                    </span>
                  </div>
                </div>

                {/* Stats */}
                <div className="mt-5 grid grid-cols-2 gap-3 lg:grid-cols-4">
                  {STATS.map((s) => (
                    <div key={s.label} className="rounded-2xl border border-[#e4d9ce] bg-white p-4 shadow-soft">
                      <p className="text-[12px] text-zinc-500 font-semibold">{s.label}</p>
                      <p className={`mt-1.5 font-heading text-3xl leading-none ${s.tone}`}>
                        {s.value}
                      </p>
                      <p className="mt-2 text-[11.5px] text-zinc-500 font-medium">
                        {s.trend}
                      </p>
                    </div>
                  ))}
                </div>

                <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-[1.3fr_1fr]">
                  {/* Open jobs */}
                  <div className="rounded-2xl border border-[#e4d9ce] bg-white shadow-soft">
                    <div className="flex items-center justify-between border-b border-border/60 px-4 py-3">
                      <p className="text-[13px] font-bold text-zinc-800">Open roles</p>
                      <span className="text-[12px] text-zinc-500 font-medium">View all</span>
                    </div>
                    <ul className="divide-y divide-[#e4d9ce]/60">
                      {JOBS.slice(0, 3).map((j) => (
                        <li key={j.role} className="flex items-center justify-between gap-3 px-4 py-3">
                          <div className="min-w-0">
                            <p className="truncate text-[13.5px] font-bold text-zinc-800">{j.role}</p>
                            <p className="text-[12px] text-zinc-500 font-medium">{j.loc} · {j.cands} candidates</p>
                          </div>
                          <span className="shrink-0 rounded-full bg-zinc-50 px-2.5 py-1 text-[11.5px] text-zinc-700 border border-[#e4d9ce] font-medium">
                            {j.stage}
                          </span>
                        </li>
                      ))}
                    </ul>
                  </div>

                  {/* Interview calendar */}
                  <div className="rounded-2xl border border-[#e4d9ce] bg-white shadow-soft">
                    <div className="flex items-center justify-between border-b border-border/60 px-4 py-3">
                      <p className="text-[13px] font-bold text-zinc-800">Today&apos;s interviews</p>
                      <span className="text-[12px] text-zinc-500 font-medium">6 scheduled</span>
                    </div>
                    <ul className="p-2">
                      {INTERVIEWS.slice(0, 3).map((it) => (
                        <li key={it.time} className="flex items-center gap-3 rounded-xl px-2 py-2 hover:bg-secondary/50">
                          <span className="w-10 text-[12px] font-semibold text-zinc-500">{it.time}</span>
                          <Avatar name={it.name} tone={it.tone} size="sm" />
                          <div className="min-w-0">
                            <p className="truncate text-[13px] font-bold text-zinc-800">{it.name}</p>
                            <p className="truncate text-[11.5px] text-zinc-500 font-medium">{it.role}</p>
                          </div>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>

                <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
                  {/* AI recommendations */}
                  <div className="rounded-2xl border border-[#4a1f2c]/15 bg-[#4a1f2c]/[0.02] p-4">
                    <div className="flex items-center gap-2">
                      <span className="grid size-5 place-items-center rounded-md bg-foreground text-background">
                        <svg viewBox="0 0 24 24" className="size-3" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                          <path d="M12 3v3M12 18v3M3 12h3M18 12h3M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1M18.4 5.6l-2.1 2.1M7.7 16.3l-2.1 2.1" />
                        </svg>
                      </span>
                      <p className="text-[13px] font-bold text-[#4a1f2c]">AI recommendations</p>
                    </div>
                    <div className="mt-3 space-y-2.5">
                      <div className="flex items-center justify-between gap-3 rounded-xl bg-white p-3 border border-[#e4d9ce]">
                        <div className="flex min-w-0 items-center gap-2.5">
                          <Avatar name="Emma Johnson" tone="green" size="sm" />
                          <div className="min-w-0">
                            <p className="truncate text-[13.5px] font-bold text-zinc-800">Emma Johnson</p>
                            <p className="truncate text-[11.5px] text-zinc-500 font-medium">Top match · Product Designer</p>
                          </div>
                        </div>
                        <span className="shrink-0 rounded-full bg-[#3c5e43]/12 px-2 py-0.5 text-[11.5px] font-bold text-[#3c5e43]">94</span>
                      </div>
                      <p className="text-[12px] leading-relaxed text-zinc-600 font-medium">
                        Move Emma to final round — her portfolio matches 8 of 9
                        role requirements and she&apos;s verified.
                      </p>
                    </div>
                  </div>

                  {/* Activity feed */}
                  <div className="rounded-2xl border border-[#e4d9ce] bg-white p-4 shadow-soft">
                    <p className="text-[13px] font-bold text-zinc-800">Recent activity</p>
                    <ul className="mt-3 space-y-3">
                      {ACTIVITY.slice(0, 3).map((a, i) => (
                        <li key={i} className="flex items-start gap-2.5">
                          <Avatar name={a.who} tone={a.tone} size="sm" />
                          <p className="text-[12.5px] leading-snug text-zinc-700">
                            <span className="font-bold text-zinc-800">{a.who}</span> {a.what}
                            <span className="ml-1 text-zinc-500 font-medium">· {a.when}</span>
                          </p>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </Reveal>
      </div>
    </section>
  )
}
