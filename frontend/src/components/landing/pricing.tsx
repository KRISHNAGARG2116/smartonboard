import { Link } from 'react-router-dom'
import { SectionLabel } from '@/components/primitives'
import { Reveal } from '@/components/reveal'

const STRENGTHS = [
  {
    num: '01',
    title: 'Agent-Led Screening',
    desc: 'Five specialized AI agents working in parallel to parse resumes, map skill gaps, and rank candidates against objective job descriptions.'
  },
  {
    num: '02',
    title: 'Assistant-Driven Workflows',
    desc: 'Recruiters remain in absolute control. AI highlights risks and matches but never auto-hires, auto-rejects, or auto-schedules.'
  },
  {
    num: '03',
    title: 'Verified Signals & Identity',
    desc: 'Mandatory Twilio SMS OTP, email OTP, and MX/DNS validation confirm candidate and recruiter identities before interactions begin.'
  },
  {
    num: '04',
    title: 'Enterprise-Grade Security',
    desc: 'Built with SOC 2 compliance, SAML/SSO integrations, automatic SCIM deprovisioning, and cryptographically isolated tenant databases.'
  }
]

export function Capabilities() {
  return (
    <section className="relative overflow-hidden w-full">
      <div className="fog-radial pointer-events-none absolute inset-0 opacity-70" />
      <div className="relative mx-auto w-full px-6 py-10 md:py-16 lg:px-12">
        <div className="grid grid-cols-1 gap-12 lg:grid-cols-2 lg:gap-16 items-start">
          
          {/* Left Column: Core pitch and CTA */}
          <Reveal className="flex flex-col justify-center text-left">
            <SectionLabel>Ecosystem Conclusion</SectionLabel>
            <h2 className="mt-4 text-balance font-heading text-4xl leading-tight text-[#1f090b] md:text-5xl">
              A verified network built for qualified decisions.
            </h2>
            <p className="mt-5 text-[15.5px] leading-relaxed text-zinc-600 font-medium max-w-xl">
              SmartOnboard is a closed, trusted hiring ecosystem designed to optimize for quality over sheer volume. We eliminate application spam by verifying every participant and delivering trusted matching signals, allowing your team to hire with quiet confidence.
            </p>
            
            {/* Final CTA Buttons */}
            <div className="mt-8 flex flex-col sm:flex-row items-stretch sm:items-center gap-4">
              <Link
                to="/recruiter/register"
                className="inline-block rounded-full bg-[#4a1f2c] px-8 py-3.5 text-[15px] font-semibold text-[#faf7f2] shadow-float transition-all hover:-translate-y-0.5 hover:bg-[#5b2434] text-center"
              >
                Create Recruiter Workspace
              </Link>
              <Link
                to="/login"
                className="text-[14.5px] font-bold text-[#4a1f2c] hover:underline underline-offset-4 text-center sm:text-left py-2"
              >
                Sign in to your account &rarr;
              </Link>
            </div>
          </Reveal>

          {/* Right Column: Strengths timeline-style list */}
          <div className="flex flex-col divide-y divide-[#e4d9ce]/60 border-t border-b lg:border-b-0 border-[#e4d9ce]/60">
            {STRENGTHS.map((s, idx) => (
              <Reveal key={s.num} delay={0.08 * (idx + 1)} className="py-6 first:pt-2 last:pb-2 text-left">
                <div className="flex gap-4">
                  <span className="font-heading text-lg font-bold text-[#4a1f2c]/50 leading-none pt-0.5 select-none">
                    {s.num}
                  </span>
                  <div>
                    <h3 className="text-[16px] font-bold text-zinc-800 leading-snug">
                      {s.title}
                    </h3>
                    <p className="mt-2 text-[13px] leading-relaxed text-zinc-500 font-medium">
                      {s.desc}
                    </p>
                  </div>
                </div>
              </Reveal>
            ))}
          </div>

        </div>
      </div>
    </section>
  )
}
