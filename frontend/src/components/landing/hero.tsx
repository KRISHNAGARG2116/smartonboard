'use client'

import { motion } from 'motion/react'
import { Link } from 'react-router-dom'
import { Avatar } from '@/components/primitives'

function Float({
  children,
  className,
  delay = 0,
  drift = 10,
}: {
  children: React.ReactNode
  className?: string
  delay?: number
  drift?: number
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 24, scale: 0.96 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: 0.8, delay, ease: [0.22, 1, 0.36, 1] }}
      className={className}
    >
      <motion.div
        animate={{ y: [0, -drift, 0] }}
        transition={{
          duration: 6 + drift / 4,
          repeat: Number.POSITIVE_INFINITY,
          ease: 'easeInOut',
          delay,
        }}
      >
        {children}
      </motion.div>
    </motion.div>
  )
}

export function Hero() {
  return (
    <section className="relative overflow-hidden">
      <div className="fog-radial pointer-events-none absolute inset-0" />
      <div className="grid-faint pointer-events-none absolute inset-0 opacity-[0.4] [mask-image:radial-gradient(60%_50%_at_50%_0%,black,transparent)]" />

      <div className="relative mx-auto max-w-6xl px-6 pb-24 pt-20 md:pt-28">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
          className="mx-auto max-w-3xl text-center"
        >
          <span className="inline-flex items-center gap-2 rounded-full border border-border bg-card/70 px-3.5 py-1.5 text-[13px] text-muted-foreground shadow-soft">
            <span className="size-1.5 rounded-full bg-success" />
            The AI Recruitment Operating System
          </span>

          <h1 className="mt-7 text-balance font-heading text-5xl leading-[1.02] text-foreground md:text-7xl">
            Hiring that runs
            <br />
            <span className="italic text-accent-ink">while you focus</span> on
            people.
          </h1>

          <p className="mx-auto mt-6 max-w-xl text-pretty text-[17px] leading-relaxed text-muted-foreground">
            SmartOnboard reads every resume, ranks every candidate and verifies
            every identity — so your team spends time on conversations, not
            screening.
          </p>

          <div className="mt-9 flex items-center justify-center gap-3">
            <Link
              to="/recruiter/register"
              className="rounded-full bg-foreground px-6 py-3 text-[15px] font-medium text-background shadow-float transition-transform hover:-translate-y-0.5"
            >
              Start hiring smarter
            </Link>
            <a
              href="#workspace"
              className="rounded-full border border-border bg-card px-6 py-3 text-[15px] font-medium text-foreground shadow-soft transition-transform hover:-translate-y-0.5"
            >
              Watch the demo
            </a>
          </div>
        </motion.div>

        {/* Floating product widgets */}
        <div className="relative mx-auto mt-16 h-[360px] max-w-5xl md:h-[420px]">
          {/* Center stage line */}
          <div className="absolute left-1/2 top-1/2 size-[420px] -translate-x-1/2 -translate-y-1/2 rounded-full border border-border/50 [mask-image:radial-gradient(circle,black,transparent_72%)]" />

          {/* AI Match */}
          <Float
            delay={0.1}
            drift={12}
            className="absolute left-0 top-2 w-[244px] md:left-6"
          >
            <div className="rounded-3xl border border-border bg-card p-5 shadow-float">
              <div className="flex items-center justify-between">
                <span className="text-[12px] font-medium text-muted-foreground">
                  AI Match Score
                </span>
                <span className="rounded-full bg-success/12 px-2 py-0.5 text-[11px] font-semibold text-success">
                  Strong fit
                </span>
              </div>
              <div className="mt-3 flex items-end gap-2">
                <span className="font-heading text-5xl leading-none text-foreground">
                  94
                </span>
                <span className="pb-1 text-[13px] text-muted-foreground">
                  /100
                </span>
              </div>
              <div className="mt-4 h-2 overflow-hidden rounded-full bg-fog">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: '94%' }}
                  transition={{ duration: 1.1, delay: 0.6, ease: 'easeOut' }}
                  className="h-full rounded-full bg-foreground"
                />
              </div>
            </div>
          </Float>

          {/* Verified Candidate */}
          <Float
            delay={0.25}
            drift={9}
            className="absolute right-0 top-0 w-[252px] md:right-8"
          >
            <div className="rounded-3xl border border-border bg-card p-5 shadow-float">
              <div className="flex items-center gap-3">
                <Avatar name="Emma Johnson" tone="green" size="lg" />
                <div className="min-w-0">
                  <p className="truncate text-[14px] font-semibold text-foreground">
                    Emma Johnson
                  </p>
                  <p className="truncate text-[12px] text-muted-foreground">
                    Senior Product Designer
                  </p>
                </div>
              </div>
              <div className="mt-4 space-y-2">
                {['Email verified', 'Phone verified', 'Identity confirmed'].map(
                  (t) => (
                    <div key={t} className="flex items-center gap-2">
                      <span className="grid size-4 place-items-center rounded-full bg-success/15 text-success">
                        <svg
                          viewBox="0 0 24 24"
                          className="size-2.5"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="3.5"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          aria-hidden="true"
                        >
                          <path d="M5 13l4 4L19 7" />
                        </svg>
                      </span>
                      <span className="text-[12.5px] text-foreground/80">
                        {t}
                      </span>
                    </div>
                  ),
                )}
              </div>
            </div>
          </Float>

          {/* Skills */}
          <Float
            delay={0.4}
            drift={11}
            className="absolute bottom-0 left-4 w-[266px] md:left-24"
          >
            <div className="rounded-3xl border border-border bg-card p-5 shadow-float">
              <p className="text-[12px] font-medium text-muted-foreground">
                Extracted skills
              </p>
              <div className="mt-3 flex flex-wrap gap-1.5">
                {[
                  'Figma',
                  'Design systems',
                  'Prototyping',
                  'User research',
                  'Accessibility',
                ].map((s) => (
                  <span
                    key={s}
                    className="rounded-full bg-secondary px-2.5 py-1 text-[12px] text-secondary-foreground ring-1 ring-inset ring-border/60"
                  >
                    {s}
                  </span>
                ))}
                <span className="rounded-full border border-dashed border-border px-2.5 py-1 text-[12px] text-muted-foreground">
                  + Design ops (gap)
                </span>
              </div>
            </div>
          </Float>

          {/* Hiring Metrics */}
          <Float
            delay={0.55}
            drift={8}
            className="absolute bottom-6 right-2 w-[230px] md:right-16"
          >
            <div className="rounded-3xl border border-border bg-card p-5 shadow-float">
              <p className="text-[12px] font-medium text-muted-foreground">
                Time to hire
              </p>
              <div className="mt-2 flex items-baseline gap-2">
                <span className="font-heading text-4xl leading-none text-foreground">
                  11
                </span>
                <span className="text-[13px] text-muted-foreground">days</span>
                <span className="ml-auto text-[12px] font-medium text-success">
                  ↓ 38%
                </span>
              </div>
              <div className="mt-4 flex h-12 items-end gap-1.5">
                {[40, 55, 48, 70, 62, 84, 78, 96].map((h, i) => (
                  <motion.span
                    key={i}
                    initial={{ height: 0 }}
                    animate={{ height: `${h}%` }}
                    transition={{
                      duration: 0.6,
                      delay: 0.7 + i * 0.05,
                      ease: 'easeOut',
                    }}
                    className="flex-1 rounded-sm bg-foreground/80"
                    style={{ minHeight: 4 }}
                  />
                ))}
              </div>
            </div>
          </Float>
        </div>

        <p className="mt-10 text-center text-[13px] uppercase tracking-[0.16em] text-muted-foreground/80">
          Trusted by recruiting teams at fast-moving companies
        </p>
        <div className="mt-5 flex flex-wrap items-center justify-center gap-x-10 gap-y-4 opacity-70">
          {['Northwind', 'Lumen', 'Atlas', 'Caldera', 'Monarch', 'Voss'].map(
            (b) => (
              <span
                key={b}
                className="text-[15px] font-semibold tracking-tight text-foreground/70"
              >
                {b}
              </span>
            ),
          )}
        </div>
      </div>
    </section>
  )
}
