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
      <div className="relative mx-auto w-full px-6 py-10 md:py-14">
        <div className="grid grid-cols-1 lg:grid-cols-[1fr_2fr] gap-8 items-center">
          {/* Left Column: Heading & Text */}
          <div className="max-w-xl">
            <SectionLabel>Emma applies</SectionLabel>
            <h2 className="mt-3 text-balance font-heading text-4xl leading-tight text-[#1f090b] md:text-5xl">
              A resume becomes a decision in seconds.
            </h2>
            <p className="mt-4 text-pretty text-[16px] leading-relaxed text-zinc-600 font-medium">
              The moment Emma applies, SmartOnboard reads her resume, extracts her
              skills, finds the gaps and shows its work — so you trust the score.
            </p>
          </div>

          {/* Right Column: Cards (nested responsive grid) */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5 w-full">
            {/* Resume Card */}
            <motion.div
              initial={{ opacity: 0, y: 28 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: '-80px' }}
              transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
              className="relative overflow-hidden rounded-[24px] border border-[#e4d9ce] bg-white p-7 shadow-float"
            >
              {/* scan line */}
              <motion.div
                initial={{ top: '0%' }}
                whileInView={{ top: ['0%', '100%', '0%'] }}
                viewport={{ once: false }}
                transition={{ duration: 4, repeat: Number.POSITIVE_INFINITY, ease: 'easeInOut' }}
                className="pointer-events-none absolute inset-x-0 h-16 bg-gradient-to-b from-transparent via-[#4a1f2c]/10 to-transparent"
              />
              <div className="flex items-center gap-3 border-b border-[#e4d9ce] pb-5">
                <Avatar name="Emma Johnson" tone="green" size="lg" />
                <div>
                  <p className="font-heading text-2xl leading-none text-[#1f090b]">Emma Johnson</p>
                  <p className="mt-1.5 text-[13px] text-zinc-500 font-semibold">Senior Product Designer · San Francisco, CA</p>
                </div>
              </div>
              <div className="space-y-5 pt-5">
                <div>
                  <p className="text-[11px] font-bold uppercase tracking-[0.14em] text-zinc-500">Experience</p>
                  <div className="mt-2.5 space-y-1">
                    <p className="text-[13.5px] font-bold text-zinc-800">Lead Product Designer — Lumen</p>
                    <p className="text-[12.5px] text-zinc-600 leading-relaxed">2020 — Present · Built and scaled the design system used across 14 products.</p>
                  </div>
                  <div className="mt-3.5 space-y-1">
                    <p className="text-[13.5px] font-bold text-zinc-800">Product Designer — Atlas</p>
                    <p className="text-[12.5px] text-zinc-600 leading-relaxed">2017 — 2020 · Led research and prototyping for the core onboarding flow.</p>
                  </div>
                </div>
                <div>
                  <p className="text-[11px] font-bold uppercase tracking-[0.14em] text-zinc-500">Highlighted skills</p>
                  <p className="mt-2.5 text-[13px] leading-relaxed text-zinc-700 font-medium">
                    <mark className="rounded bg-success/15 px-1.5 py-0.5 text-emerald-950 font-bold">Figma</mark>,{' '}
                    <mark className="rounded bg-success/15 px-1.5 py-0.5 text-emerald-950 font-bold">design systems</mark>,{' '}
                    <mark className="rounded bg-success/15 px-1.5 py-0.5 text-emerald-950 font-bold">prototyping</mark>,{' '}
                    <mark className="rounded bg-success/15 px-1.5 py-0.5 text-emerald-950 font-bold">user research</mark> and{' '}
                    <mark className="rounded bg-success/15 px-1.5 py-0.5 text-emerald-950 font-bold">accessibility</mark>.
                  </p>
                </div>
              </div>
            </motion.div>

            {/* AI Analysis Card */}
            <motion.div
              initial={{ opacity: 0, y: 28 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: '-80px' }}
              transition={{ duration: 0.7, delay: 0.12, ease: [0.22, 1, 0.36, 1] }}
              className="rounded-[24px] border border-[#e4d9ce] bg-white p-7 shadow-float"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="grid size-6 place-items-center rounded-lg bg-foreground text-background">
                    <svg viewBox="0 0 24 24" className="size-3.5" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                      <path d="M12 3v3M12 18v3M3 12h3M18 12h3M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1M18.4 5.6l-2.1 2.1M7.7 16.3l-2.1 2.1" />
                    </svg>
                  </span>
                  <p className="text-[14px] font-bold text-[#1f090b]">AI analysis</p>
                </div>
                <span className="rounded-full bg-[#3c5e43]/12 px-2.5 py-1 text-[12px] font-bold text-[#3c5e43]">Strong fit · 94</span>
              </div>

              {/* Confidence */}
              <div className="mt-6">
                <div className="flex items-center justify-between text-[12.5px] font-medium">
                  <span className="text-zinc-500">Match confidence</span>
                  <span className="font-bold text-[#1f090b]">94%</span>
                </div>
                <div className="mt-2 h-2 overflow-hidden rounded-full bg-[#faf7f2] border border-[#e4d9ce]/60">
                  <motion.div
                    initial={{ width: 0 }}
                    whileInView={{ width: '94%' }}
                    viewport={{ once: true }}
                    transition={{ duration: 1.1, delay: 0.3, ease: 'easeOut' }}
                    className="h-full rounded-full bg-[#4a1f2c]"
                  />
                </div>
              </div>

              {/* Matched skills */}
              <div className="mt-6">
                <p className="text-[12px] font-semibold text-zinc-500">Skills matched to role</p>
                <div className="mt-2.5 flex flex-wrap gap-1.5">
                  {MATCHED.map((s) => (
                    <span key={s} className="inline-flex items-center gap-1 rounded-full bg-[#faf7f2] px-2.5 py-1 text-[12px] text-zinc-800 border border-[#e4d9ce] font-medium">
                      <svg viewBox="0 0 24 24" className="size-2.5 text-[#3c5e43]" fill="none" stroke="currentColor" strokeWidth="3.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                        <path d="M5 13l4 4L19 7" />
                      </svg>
                      {s}
                    </span>
                  ))}
                </div>
              </div>

              {/* Gaps to explore */}
              <div className="mt-5">
                <p className="text-[12px] font-semibold text-zinc-500">Gaps to explore</p>
                <div className="mt-2.5 flex flex-wrap gap-1.5">
                  {MISSING.map((s) => (
                    <span key={s} className="rounded-full border border-dashed border-[#e4d9ce] bg-white px-2.5 py-1 text-[12px] text-zinc-500 font-medium">
                      {s}
                    </span>
                  ))}
                </div>
              </div>

              {/* Reasoning */}
              <div className="mt-6 rounded-2xl bg-[#4a1f2c]/[0.02] p-4 border border-[#4a1f2c]/10">
                <p className="text-[12px] font-bold text-[#4a1f2c]">Why SmartOnboard recommends Emma</p>
                <ul className="mt-2.5 space-y-2">
                  {REASONS.map((r) => (
                    <li key={r} className="flex items-start gap-2 text-[12.5px] leading-snug text-zinc-700">
                      <span className="mt-1.5 size-1.5 shrink-0 rounded-full bg-[#4a1f2c]" />
                      {r}
                    </li>
                  ))}
                </ul>
              </div>
            </motion.div>
          </div>
        </div>
      </div>
    </section>
  )
}
