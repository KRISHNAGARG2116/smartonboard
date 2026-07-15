import { Link } from 'react-router-dom'
import { SectionLabel } from '@/components/primitives'
import { Reveal } from '@/components/reveal'

const INCLUDED = [
  'Unlimited roles & candidates',
  'AI resume parsing & ranking',
  'Skill gap analysis',
  'Email, phone & identity verification',
  'Collaborative hiring workspace',
  'Interview scheduling',
  'Executive analytics',
  'SSO, audit logs & RBAC',
]

export function Pricing() {
  return (
    <section className="relative overflow-hidden">
      <div className="fog-radial pointer-events-none absolute inset-0 opacity-70" />
      <div className="relative mx-auto max-w-6xl px-6 py-20 md:py-28">
        <Reveal className="mx-auto max-w-2xl text-center">
          <SectionLabel className="justify-center">Pricing</SectionLabel>
          <h2 className="mt-5 text-balance font-heading text-4xl leading-tight text-[#1f090b] md:text-5xl">
            One plan. Everything your team needs to hire.
          </h2>
        </Reveal>

        <Reveal delay={0.1} className="mx-auto mt-12 max-w-md">
          <div className="overflow-hidden rounded-[28px] border border-[#e4d9ce] bg-white shadow-float">
            <div className="border-b border-[#e4d9ce]/60 p-8 text-center">
              <p className="text-[13px] font-bold uppercase tracking-[0.16em] text-zinc-500">
                SmartOnboard for teams
              </p>
              <div className="mt-5 flex items-baseline justify-center gap-1.5">
                <span className="font-heading text-6xl leading-none text-[#1f090b]">$49</span>
                <span className="text-[15px] text-zinc-500 font-bold">/ month per active job</span>
              </div>
              <p className="mt-3 text-[14px] text-zinc-600 font-medium">
                Billed monthly · Unlimited candidates & screening
              </p>
              <Link
                to="/recruiter/register"
                className="mt-7 inline-block w-full rounded-full bg-[#4a1f2c] px-6 py-3.5 text-[15px] font-semibold text-[#faf7f2] shadow-float transition-all hover:-translate-y-0.5 hover:bg-[#5b2434] text-center"
              >
                Start Recruiting
              </Link>
            </div>
            <ul className="grid grid-cols-1 gap-3 p-8 sm:grid-cols-2">
              {INCLUDED.map((f) => (
                <li key={f} className="flex items-start gap-2.5 text-[13.5px] text-zinc-700 font-medium">
                  <span className="mt-0.5 grid size-4 shrink-0 place-items-center rounded-full bg-[#3c5e43]/12 text-[#3c5e43]">
                    <svg viewBox="0 0 24 24" className="size-2.5" fill="none" stroke="currentColor" strokeWidth="3.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                      <path d="M5 13l4 4L19 7" />
                    </svg>
                  </span>
                  {f}
                </li>
              ))}
            </ul>
          </div>
          <p className="mt-5 text-center text-[13px] text-zinc-500 font-medium">
            Need more than 25 seats?{' '}
            <a href="#" className="font-bold text-[#4a1f2c] underline underline-offset-4 hover:text-[#5b2434]">
              Talk to sales
            </a>
          </p>
        </Reveal>
      </div>
    </section>
  )
}
