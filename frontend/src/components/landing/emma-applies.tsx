'use client'

import { motion } from 'motion/react'
import { Avatar, SectionLabel } from '@/components/primitives'

const MATCHED = ['Figma', 'Design systems', 'Prototyping', 'User research', 'Accessibility', 'Design tokens', 'Usability testing', 'Wireframing']
const MISSING = ['Design ops', 'Motion design']

const REASONS = [
  '8 of 9 role requirements matched in work history',
  '6 years leading design systems at scale',
  'Identity, email and phone verified',
]

export function EmmaApplies() {
  return (
    <section className="relative overflow-hidden">
      <div className="fog-radial pointer-events-none absolute inset-0 opacity-60" />
      <div className="relative mx-auto max-w-6xl px-6 py-20 md:py-28">
        <div className="max-w-2xl">
          <SectionLabel>Emma applies</SectionLabel>
          <h2 className="mt-5 text-balance font-heading text-4xl leading-tight text-foreground md:text-5xl">
            A resume becomes a decision in seconds.
          </h2>
          <p className="mt-4 max-w-xl text-pretty text-[16px] leading-relaxed text-muted-foreground">
            The moment Emma applies, SmartOnboard reads her resume, extracts her
            skills, finds the gaps and shows its work — so you trust the score.
          </p>
        </div>

        <div className="mt-12 grid grid-cols-1 gap-5 lg:grid-cols-[1fr_1.1fr]">
          {/* Resume */}
          <motion.div
            initial={{ opacity: 0, y: 28 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: '-80px' }}
            transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
            className="relative overflow-hidden rounded-[24px] border border-border bg-card p-7 shadow-float"
          >
            {/* scan line */}
            <motion.div
              initial={{ top: '0%' }}
              whileInView={{ top: ['0%', '100%', '0%'] }}
              viewport={{ once: false }}
              transition={{ duration: 4, repeat: Number.POSITIVE_INFINITY, ease: 'easeInOut' }}
              className="pointer-events-none absolute inset-x-0 h-16 bg-gradient-to-b from-transparent via-success/10 to-transparent"
            />
            <div className="flex items-center gap-3 border-b border-border/60 pb-5">
              <Avatar name="Emma Johnson" tone="green" size="lg" />
              <div>
                <p className="font-heading text-2xl leading-none text-foreground">Emma Johnson</p>
                <p className="mt-1 text-[13px] text-muted-foreground">Senior Product Designer · San Francisco, CA</p>
              </div>
            </div>
            <div className="space-y-5 pt-5">
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">Experience</p>
                <div className="mt-2 space-y-1">
                  <p className="text-[13.5px] font-medium text-foreground">Lead Product Designer — Lumen</p>
                  <p className="text-[12.5px] text-muted-foreground">2020 — Present · Built and scaled the design system used across 14 products.</p>
                </div>
                <div className="mt-3 space-y-1">
                  <p className="text-[13.5px] font-medium text-foreground">Product Designer — Atlas</p>
                  <p className="text-[12.5px] text-muted-foreground">2017 — 2020 · Led research and prototyping for the core onboarding flow.</p>
                </div>
              </div>
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">Highlighted skills</p>
                <p className="mt-2 text-[13px] leading-relaxed text-foreground/80">
                  <mark className="rounded bg-success/15 px-1 text-foreground">Figma</mark>,{' '}
                  <mark className="rounded bg-success/15 px-1 text-foreground">design systems</mark>,{' '}
                  <mark className="rounded bg-success/15 px-1 text-foreground">prototyping</mark>,{' '}
                  <mark className="rounded bg-success/15 px-1 text-foreground">user research</mark> and{' '}
                  <mark className="rounded bg-success/15 px-1 text-foreground">accessibility</mark>.
                </p>
              </div>
            </div>
          </motion.div>

          {/* AI analysis */}
          <motion.div
            initial={{ opacity: 0, y: 28 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: '-80px' }}
            transition={{ duration: 0.7, delay: 0.12, ease: [0.22, 1, 0.36, 1] }}
            className="rounded-[24px] border border-border bg-card p-7 shadow-float"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="grid size-6 place-items-center rounded-lg bg-foreground text-background">
                  <svg viewBox="0 0 24 24" className="size-3.5" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                    <path d="M12 3v3M12 18v3M3 12h3M18 12h3M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1M18.4 5.6l-2.1 2.1M7.7 16.3l-2.1 2.1" />
                  </svg>
                </span>
                <p className="text-[14px] font-semibold text-foreground">AI analysis</p>
              </div>
              <span className="rounded-full bg-success/12 px-2.5 py-1 text-[12px] font-semibold text-success">Strong fit · 94</span>
            </div>

            {/* Confidence */}
            <div className="mt-6">
              <div className="flex items-center justify-between text-[12.5px]">
                <span className="text-muted-foreground">Match confidence</span>
                <span className="font-medium text-foreground">94%</span>
              </div>
              <div className="mt-2 h-2 overflow-hidden rounded-full bg-fog">
                <motion.div
                  initial={{ width: 0 }}
                  whileInView={{ width: '94%' }}
                  viewport={{ once: true }}
                  transition={{ duration: 1.1, delay: 0.3, ease: 'easeOut' }}
                  className="h-full rounded-full bg-foreground"
                />
              </div>
            </div>

            {/* Matched skills */}
            <div className="mt-6">
              <p className="text-[12px] font-medium text-muted-foreground">Skills matched to role</p>
              <div className="mt-2.5 flex flex-wrap gap-1.5">
                {MATCHED.map((s) => (
                  <span key={s} className="inline-flex items-center gap-1 rounded-full bg-success/10 px-2.5 py-1 text-[12px] text-foreground ring-1 ring-inset ring-success/20">
                    <svg viewBox="0 0 24 24" className="size-2.5 text-success" fill="none" stroke="currentColor" strokeWidth="3.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                      <path d="M5 13l4 4L19 7" />
                    </svg>
                    {s}
                  </span>
                ))}
              </div>
            </div>

            {/* Missing skills */}
            <div className="mt-5">
              <p className="text-[12px] font-medium text-muted-foreground">Gaps to explore</p>
              <div className="mt-2.5 flex flex-wrap gap-1.5">
                {MISSING.map((s) => (
                  <span key={s} className="rounded-full border border-dashed border-border px-2.5 py-1 text-[12px] text-muted-foreground">
                    {s}
                  </span>
                ))}
              </div>
            </div>

            {/* Reasoning */}
            <div className="mt-6 rounded-2xl bg-secondary/50 p-4 ring-1 ring-inset ring-border/60">
              <p className="text-[12px] font-medium text-foreground">Why SmartOnboard recommends Emma</p>
              <ul className="mt-2.5 space-y-2">
                {REASONS.map((r) => (
                  <li key={r} className="flex items-start gap-2 text-[12.5px] leading-snug text-foreground/80">
                    <span className="mt-1 size-1.5 shrink-0 rounded-full bg-foreground" />
                    {r}
                  </li>
                ))}
              </ul>
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  )
}
