import { Link } from 'react-router-dom'
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
    <header className="sticky top-0 z-50 border-b border-[#4a1f2c]/20 bg-[#250e15] text-[#faf7f2]">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-6">
        <Link to="/" aria-label="SmartOnboard home">
          <Logo className="text-[#faf7f2]" />
        </Link>
        <nav className="hidden items-center gap-8 md:flex" aria-label="Primary">
          {NAV.map((item) => (
            <a
              key={item.label}
              href={item.href}
              className="text-[14px] text-[#e4d9ce] transition-colors hover:text-[#faf7f2]"
            >
              {item.label}
            </a>
          ))}
        </nav>
        <div className="flex items-center gap-2">
          <Link
            to="/login"
            className="hidden rounded-full px-4 py-2 text-[14px] text-[#e4d9ce] transition-colors hover:text-[#faf7f2] sm:inline-block"
          >
            Sign in
          </Link>
          <Link
            to="/recruiter/register"
            className="rounded-full bg-[#faf7f2] px-4 py-2 text-[14px] font-semibold text-[#250e15] shadow-soft transition-transform hover:-translate-y-px hover:bg-white"
          >
            Start Recruiting
          </Link>
        </div>
      </div>
    </header>
  )
}
