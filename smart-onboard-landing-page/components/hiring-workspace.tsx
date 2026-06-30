import { Avatar, SectionLabel, WindowChrome } from '@/components/primitives'
import { Reveal } from '@/components/reveal'

type Card = {
  name: string
  role: string
  score: number
  tone: 'slate' | 'green' | 'amber' | 'rose' | 'blue'
  tags: string[]
  verified?: boolean
}

const COLUMNS: { title: string; count: number; cards: Card[] }[] = [
  {
    title: 'Applied',
    count: 42,
    cards: [
      { name: 'Liam Carter', role: 'Product Designer', score: 71, tone: 'slate', tags: ['Figma', 'UI'] },
      { name: 'Sofia Reyes', role: 'Product Designer', score: 68, tone: 'amber', tags: ['Research'] },
    ],
  },
  {
    title: 'Screening',
    count: 14,
    cards: [
      { name: 'Marcus Lee', role: 'Product Designer', score: 88, tone: 'blue', tags: ['Systems', 'Prototyping'], verified: true },
      { name: 'Hana Kim', role: 'Product Designer', score: 79, tone: 'rose', tags: ['Mobile'] },
    ],
  },
  {
    title: 'Interview',
    count: 6,
    cards: [
      { name: 'Emma Johnson', role: 'Product Designer', score: 94, tone: 'green', tags: ['Systems', 'A11y'], verified: true },
      { name: 'David Okafor', role: 'Product Designer', score: 82, tone: 'slate', tags: ['Research'], verified: true },
    ],
  },
  {
    title: 'Offer',
    count: 2,
    cards: [
      { name: 'Priya Nair', role: 'Product Designer', score: 91, tone: 'amber', tags: ['Brand'], verified: true },
    ],
  },
]

export function HiringWorkspace() {
  return (
    <section id="workspace" className="mx-auto max-w-6xl px-6 py-20 md:py-28">
      <Reveal className="max-w-2xl">
        <SectionLabel>The hiring workspace</SectionLabel>
        <h2 className="mt-5 text-balance font-heading text-4xl leading-tight text-foreground md:text-5xl">
          Your whole team, moving candidates forward together.
        </h2>
        <p className="mt-4 max-w-xl text-pretty text-[16px] leading-relaxed text-muted-foreground">
          A living pipeline where every card carries its score, its status and
          its history. Comment, schedule and decide without leaving the board.
        </p>
      </Reveal>

      <Reveal delay={0.1} className="mt-12">
        <div className="overflow-hidden rounded-[24px] border border-border bg-card shadow-float">
          <WindowChrome label="app.smartonboard.com/jobs/product-designer" />

          <div className="grid grid-cols-1 lg:grid-cols-[1fr_300px]">
            {/* Board */}
            <div className="overflow-x-auto border-b border-border/60 p-4 lg:border-b-0 lg:border-r">
              <div className="flex min-w-[640px] gap-3">
                {COLUMNS.map((col) => (
                  <div key={col.title} className="flex-1">
                    <div className="mb-2.5 flex items-center justify-between px-1">
                      <span className="text-[13px] font-semibold text-foreground">{col.title}</span>
                      <span className="rounded-full bg-secondary px-2 py-0.5 text-[11px] text-muted-foreground ring-1 ring-inset ring-border/60">
                        {col.count}
                      </span>
                    </div>
                    <div className="space-y-2.5 rounded-2xl bg-secondary/40 p-2">
                      {col.cards.map((c) => (
                        <article key={c.name} className="rounded-xl border border-border/70 bg-card p-3 shadow-soft">
                          <div className="flex items-center justify-between">
                            <div className="flex min-w-0 items-center gap-2">
                              <Avatar name={c.name} tone={c.tone} size="sm" />
                              <div className="min-w-0">
                                <p className="flex items-center gap-1 truncate text-[13px] font-medium text-foreground">
                                  {c.name}
                                  {c.verified ? (
                                    <svg viewBox="0 0 24 24" className="size-3 text-success" fill="currentColor" aria-hidden="true">
                                      <path d="m9 12 2 2 4-4m-3-8 2.4 1.4 2.8-.2 1 2.6 2.2 1.8-1 2.6 1 2.6-2.2 1.8-1 2.6-2.8-.2L12 22l-2.4-1.4-2.8.2-1-2.6L3.6 16.4l1-2.6-1-2.6 2.2-1.8 1-2.6 2.8.2z" opacity="0.18" />
                                    </svg>
                                  ) : null}
                                </p>
                                <p className="truncate text-[11px] text-muted-foreground">{c.role}</p>
                              </div>
                            </div>
                            <span className={`shrink-0 text-[12px] font-semibold ${c.score >= 90 ? 'text-success' : 'text-foreground'}`}>{c.score}</span>
                          </div>
                          <div className="mt-2.5 flex flex-wrap gap-1">
                            {c.tags.map((t) => (
                              <span key={t} className="rounded-md bg-secondary px-1.5 py-0.5 text-[10.5px] text-secondary-foreground ring-1 ring-inset ring-border/50">
                                {t}
                              </span>
                            ))}
                          </div>
                        </article>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Candidate detail + comments */}
            <aside className="p-4">
              <div className="flex items-center gap-3">
                <Avatar name="Emma Johnson" tone="green" size="lg" />
                <div className="min-w-0">
                  <p className="flex items-center gap-1.5 text-[14px] font-semibold text-foreground">
                    Emma Johnson
                    <span className="rounded-full bg-success/12 px-1.5 py-0.5 text-[10.5px] font-semibold text-success">94</span>
                  </p>
                  <p className="text-[12px] text-muted-foreground">Interview · final round</p>
                </div>
              </div>

              <div className="mt-4 grid grid-cols-3 gap-2 text-center">
                {[
                  { k: 'Stage', v: 'Final' },
                  { k: 'Owner', v: 'Sarah' },
                  { k: 'Source', v: 'Referral' },
                ].map((m) => (
                  <div key={m.k} className="rounded-xl bg-secondary/50 py-2 ring-1 ring-inset ring-border/50">
                    <p className="text-[10.5px] uppercase tracking-wide text-muted-foreground">{m.k}</p>
                    <p className="mt-0.5 text-[12.5px] font-medium text-foreground">{m.v}</p>
                  </div>
                ))}
              </div>

              {/* Schedule */}
              <div className="mt-4 flex items-center justify-between rounded-xl border border-border/70 bg-background p-3">
                <div className="flex items-center gap-2">
                  <span className="grid size-7 place-items-center rounded-lg bg-secondary text-foreground">
                    <svg viewBox="0 0 24 24" className="size-4" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
                      <path d="M7 3v4M17 3v4M4 9h16M5 5h14v16H5z" />
                    </svg>
                  </span>
                  <div>
                    <p className="text-[12.5px] font-medium text-foreground">Panel interview</p>
                    <p className="text-[11px] text-muted-foreground">Wed · 11:00 AM</p>
                  </div>
                </div>
                <span className="rounded-full bg-foreground px-2.5 py-1 text-[11px] font-medium text-background">Scheduled</span>
              </div>

              {/* Comments */}
              <div className="mt-4">
                <p className="text-[12px] font-medium text-muted-foreground">Team notes</p>
                <div className="mt-2.5 space-y-3">
                  <div className="flex items-start gap-2">
                    <Avatar name="Sarah Chen" tone="ink" size="sm" />
                    <div className="rounded-xl rounded-tl-sm bg-secondary/60 px-3 py-2">
                      <p className="text-[12px] leading-snug text-foreground/85">Portfolio is exceptional — strongest systems work I&apos;ve seen this quarter.</p>
                    </div>
                  </div>
                  <div className="flex items-start gap-2">
                    <Avatar name="Raj Patel" tone="blue" size="sm" />
                    <div className="rounded-xl rounded-tl-sm bg-secondary/60 px-3 py-2">
                      <p className="text-[12px] leading-snug text-foreground/85">Agreed. Let&apos;s fast-track to final. <span className="text-muted-foreground">@sarah</span></p>
                    </div>
                  </div>
                </div>
                <div className="mt-3 flex items-center gap-2 rounded-full border border-border bg-background px-3 py-2">
                  <span className="text-[12px] text-muted-foreground">Add a note…</span>
                  <span className="ml-auto grid size-6 place-items-center rounded-full bg-foreground text-background">
                    <svg viewBox="0 0 24 24" className="size-3" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                      <path d="M5 12h14M13 6l6 6-6 6" />
                    </svg>
                  </span>
                </div>
              </div>
            </aside>
          </div>
        </div>
      </Reveal>
    </section>
  )
}
