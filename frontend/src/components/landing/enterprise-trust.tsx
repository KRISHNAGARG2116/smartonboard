import { SectionLabel } from '@/components/primitives'
import { Reveal } from '@/components/reveal'

const ITEMS = [
  {
    title: 'Audit logs',
    body: 'Every decision, comment and status change is recorded and exportable.',
    icon: 'M9 12h6M9 16h6M9 8h2M7 3h7l5 5v13H5V3z',
  },
  {
    title: 'Verified identities',
    body: 'Email, phone and document verification built into every candidate.',
    icon: 'M12 3l8 3v5c0 5-3.4 8.5-8 10-4.6-1.5-8-5-8-10V6z',
  },
  {
    title: 'Security',
    body: 'SOC 2 Type II, encryption at rest and in transit, SSO and SAML.',
    icon: 'M12 2 4 6v6c0 5 3.5 8 8 10 4.5-2 8-5 8-10V6z',
  },
  {
    title: 'Permissions',
    body: 'Granular role-based access keeps the right people on the right roles.',
    icon: 'M17 11V7a5 5 0 0 0-10 0v4M5 11h14v10H5z',
  },
]

export function EnterpriseTrust() {
  return (
    <section className="mx-auto max-w-6xl px-6 py-4 md:py-6">
      <Reveal className="flex flex-col items-start justify-between gap-6 md:flex-row md:items-end">
        <div className="max-w-md">
          <SectionLabel>Enterprise trust</SectionLabel>
          <h2 className="mt-5 text-balance font-heading text-2xl leading-tight text-[#1f090b] md:text-3xl">
            Quietly secure, by default.
          </h2>
        </div>
        <p className="max-w-sm text-pretty text-[14px] leading-relaxed text-zinc-600 font-medium">
          The controls your security and compliance teams expect — without the
          friction your recruiters notice.
        </p>
      </Reveal>

      <Reveal delay={0.1} className="mt-5 grid grid-cols-1 gap-px overflow-hidden rounded-[24px] border border-[#e4d9ce] bg-[#e4d9ce] sm:grid-cols-2 lg:grid-cols-4">
        {ITEMS.map((item) => (
          <div key={item.title} className="bg-white p-4.5">
            <span className="grid size-8 place-items-center rounded-xl bg-[#faf7f2] text-[#4a1f2c] border border-[#e4d9ce]/40">
              <svg viewBox="0 0 24 24" className="size-4.5" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d={item.icon} />
              </svg>
            </span>
            <h3 className="mt-4 text-[15px] font-bold text-zinc-800">{item.title}</h3>
            <p className="mt-1.5 text-[13.5px] leading-relaxed text-zinc-600 font-medium">{item.body}</p>
          </div>
        ))}
      </Reveal>
    </section>
  )
}
