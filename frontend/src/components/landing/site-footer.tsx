import { Logo } from '@/components/primitives'

const COLS = [
  {
    title: 'Product',
    links: ['Overview', 'Workspace', 'AI screening', 'Analytics', 'Pricing'],
  },
  {
    title: 'Company',
    links: ['About', 'Customers', 'Careers', 'Blog'],
  },
  {
    title: 'Resources',
    links: ['Documentation', 'Security', 'Status', 'Contact'],
  },
]

export function FooterNav() {
  return (
    <section className="border-t border-[#e4d9ce] bg-[#faf7f2]/80 backdrop-blur-sm relative z-10 w-full">
      <div className="mx-auto max-w-6xl px-6 py-14">
        <div className="grid grid-cols-2 gap-10 md:grid-cols-[1.5fr_1fr_1fr_1fr]">
          <div>
            <Logo className="text-[#1f090b]" />
            <p className="mt-4 max-w-xs text-[13.5px] leading-relaxed text-zinc-500 font-medium">
              The AI Recruitment Operating System for teams who hire on evidence, not guesswork.
            </p>
          </div>
          {COLS.map((col) => (
            <div key={col.title} className="text-left">
              <p className="text-[13px] font-bold text-[#1f090b]">{col.title}</p>
              <ul className="mt-4 space-y-3">
                {col.links.map((l) => (
                  <li key={l}>
                    <a
                      href="#"
                      className="text-[13.5px] text-zinc-500 font-medium transition-colors hover:text-[#4a1f2c]"
                    >
                      {l}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

export function SiteFooter() {
  return (
    <footer className="bg-[#250e15] text-[#e4d9ce] border-t border-[#4a1f2c]/10 relative z-10">
      <div className="mx-auto max-w-6xl px-6 py-6 flex flex-col items-center justify-between gap-3 text-[12.5px] sm:flex-row">
        <p>© 2026 SmartOnboard, Inc. All rights reserved.</p>
        <div className="flex gap-6">
          <a href="#" className="transition-colors hover:text-[#faf7f2]">Privacy</a>
          <a href="#" className="transition-colors hover:text-[#faf7f2]">Terms</a>
          <a href="#" className="transition-colors hover:text-[#faf7f2]">Security</a>
        </div>
      </div>
    </footer>
  )
}
