import { Link } from 'react-router-dom'
import { SectionLabel } from '@/components/primitives'
import { Reveal } from '@/components/reveal'
import { ShieldCheck, CheckCircle2, SearchCode, Sparkles } from 'lucide-react'

const CAPABILITIES = [
  {
    title: 'Verified Identities',
    description: 'Twilio SMS and email OTP validation confirms candidates are real before you review.',
    icon: ShieldCheck
  },
  {
    title: 'Applicability Matching',
    description: 'Compare candidate experience against the job description with clear match indicators.',
    icon: Sparkles
  },
  {
    title: 'Evidence-Led Screening',
    description: 'Highlight verification logs, matched skills, and potential profile discrepancies.',
    icon: CheckCircle2
  },
  {
    title: 'Structured Workflows',
    description: 'Recruiters stay in control with smart assistant tools, not auto-hires or auto-rejects.',
    icon: SearchCode
  }
]

export function Capabilities() {
  return (
    <section className="relative overflow-hidden">
      <div className="fog-radial pointer-events-none absolute inset-0 opacity-70" />
      <div className="relative mx-auto w-full px-6 py-10 md:py-14">
        {/* Centered header copy on top */}
        <Reveal className="mx-auto max-w-2xl text-center mb-10">
          <SectionLabel className="justify-center">Capabilities</SectionLabel>
          <h2 className="mt-3 text-balance font-heading text-4xl leading-tight text-[#1f090b] md:text-5xl">
            AI Recruiting Capabilities
          </h2>
          <p className="mt-3 text-[16px] text-zinc-600 font-medium max-w-xl mx-auto">
            A closed, trusted ecosystem designed to prioritize signal quality over candidate volume.
          </p>
        </Reveal>

        {/* Centered 2x2 capabilities grid below */}
        <Reveal delay={0.1} className="mx-auto max-w-4xl">
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
            {CAPABILITIES.map((c) => {
              const Icon = c.icon
              return (
                <div key={c.title} className="rounded-2xl border border-[#e4d9ce] bg-white p-5 shadow-soft flex gap-4">
                  <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-[#faf7f2] text-[#4a1f2c] border border-[#e4d9ce]/40">
                    <Icon className="size-5" />
                  </span>
                  <div>
                    <h3 className="text-[16px] font-bold text-zinc-800">{c.title}</h3>
                    <p className="mt-1.5 text-[13.5px] leading-relaxed text-zinc-600 font-medium">{c.description}</p>
                  </div>
                </div>
              )
            })}
          </div>

          <div className="mt-10 text-center">
            <Link
              to="/recruiter/register"
              className="inline-block rounded-full bg-[#4a1f2c] px-8 py-3.5 text-[15px] font-semibold text-[#faf7f2] shadow-float transition-all hover:-translate-y-0.5 hover:bg-[#5b2434]"
            >
              Start Recruiting
            </Link>
          </div>
        </Reveal>
      </div>
    </section>
  )
}
