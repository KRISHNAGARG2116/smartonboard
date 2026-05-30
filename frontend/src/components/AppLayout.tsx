import type { ReactNode } from 'react'
import Header from './Header'

interface AppLayoutProps {
  children: ReactNode
}

export default function AppLayout({ children }: AppLayoutProps) {
  return (
    <div className="app-shell">
      <Header />
      <main className="app-main" id="main-content">
        {children}
      </main>
    </div>
  )
}
