import Link from 'next/link'
import { Logo } from '@/components/primitives'

const NAV = [
  { label: 'Product', href: '#product' },
  { label: 'Workspace', href: '#workspace' },
  { label: 'Outcomes', href: '#outcomes' },
  { label: 'Enterprise', href: '#enterprise' },
  { label: 'Pricing', href: '#pricing' },
]

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-50 border-b border-border/60 bg-background/80 backdrop-blur-xl">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-6">
        <Link href="/" aria-label="SmartOnboard home">
          <Logo />
        </Link>
        <nav className="hidden items-center gap-8 md:flex" aria-label="Primary">
          {NAV.map((item) => (
            <a
              key={item.label}
              href={item.href}
              className="text-[14px] text-muted-foreground transition-colors hover:text-foreground"
            >
              {item.label}
            </a>
          ))}
        </nav>
        <div className="flex items-center gap-2">
          <a
            href="#"
            className="hidden rounded-full px-4 py-2 text-[14px] text-muted-foreground transition-colors hover:text-foreground sm:inline-block"
          >
            Sign in
          </a>
          <a
            href="#pricing"
            className="rounded-full bg-foreground px-4 py-2 text-[14px] font-medium text-background shadow-soft transition-transform hover:-translate-y-px"
          >
            Book a demo
          </a>
        </div>
      </div>
    </header>
  )
}
