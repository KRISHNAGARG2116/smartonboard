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
    <footer className="border-t border-border bg-background">
      <div className="mx-auto max-w-6xl px-6 py-14">
        <div className="grid grid-cols-2 gap-10 md:grid-cols-[1.5fr_1fr_1fr_1fr]">
          <div>
            <Logo />
            <p className="mt-4 max-w-xs text-[13.5px] leading-relaxed text-muted-foreground">
              The AI Recruitment Operating System for teams who hire on
              evidence, not guesswork.
            </p>
          </div>
          {COLS.map((col) => (
            <div key={col.title}>
              <p className="text-[13px] font-semibold text-foreground">{col.title}</p>
              <ul className="mt-3 space-y-2.5">
                {col.links.map((l) => (
                  <li key={l}>
                    <a href="#" className="text-[13.5px] text-muted-foreground transition-colors hover:text-foreground">
                      {l}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
        <div className="mt-12 flex flex-col items-start justify-between gap-3 border-t border-border pt-6 text-[12.5px] text-muted-foreground sm:flex-row sm:items-center">
          <p>© 2026 SmartOnboard, Inc. All rights reserved.</p>
          <div className="flex gap-6">
            <a href="#" className="transition-colors hover:text-foreground">Privacy</a>
            <a href="#" className="transition-colors hover:text-foreground">Terms</a>
            <a href="#" className="transition-colors hover:text-foreground">Security</a>
          </div>
        </div>
      </div>
    </footer>
  )
}
