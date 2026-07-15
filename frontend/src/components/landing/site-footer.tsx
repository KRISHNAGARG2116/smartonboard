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

export function SiteFooter() {
  return (
    <footer className="border-t border-[#4a1f2c]/20 bg-[#250e15] text-[#e4d9ce]">
      <div className="mx-auto max-w-6xl px-6 py-14">
        <div className="grid grid-cols-2 gap-10 md:grid-cols-[1.5fr_1fr_1fr_1fr]">
          <div>
            <Logo className="text-[#faf7f2]" />
            <p className="mt-4 max-w-xs text-[13.5px] leading-relaxed text-[#e4d9ce]">
              The AI Recruitment Operating System for teams who hire on
              evidence, not guesswork.
            </p>
          </div>
          {COLS.map((col) => (
            <div key={col.title}>
              <p className="text-[13px] font-semibold text-[#faf7f2]">{col.title}</p>
              <ul className="mt-3 space-y-2.5">
                {col.links.map((l) => (
                  <li key={l}>
                    <a href="#" className="text-[13.5px] text-[#e4d9ce] transition-colors hover:text-[#faf7f2]">
                      {l}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
        <div className="mt-12 flex flex-col items-start justify-between gap-3 border-t border-[#4a1f2c]/20 pt-6 text-[12.5px] text-[#e4d9ce] sm:flex-row sm:items-center">
          <p>© 2026 SmartOnboard, Inc. All rights reserved.</p>
          <div className="flex gap-6">
            <a href="#" className="transition-colors hover:text-[#faf7f2]">Privacy</a>
            <a href="#" className="transition-colors hover:text-[#faf7f2]">Terms</a>
            <a href="#" className="transition-colors hover:text-[#faf7f2]">Security</a>
          </div>
        </div>
      </div>
    </footer>
  )
}
