import { SiteHeader } from '../components/landing/site-header'
import { Hero } from '../components/landing/hero'
import { RecruiterDashboard } from '../components/landing/recruiter-dashboard'
import { EmmaApplies } from '../components/landing/emma-applies'
import { HiringWorkspace } from '../components/landing/hiring-workspace'
import { BusinessOutcomes } from '../components/landing/business-outcomes'
import { EnterpriseTrust } from '../components/landing/enterprise-trust'
import { Pricing } from '../components/landing/pricing'
import { SiteFooter } from '../components/landing/site-footer'

export default function Landing() {
  return (
    <div className="min-h-screen bg-background font-sans">
      <SiteHeader />
      <main>
        <Hero />
        <RecruiterDashboard />
        <EmmaApplies />
        <HiringWorkspace />
        <BusinessOutcomes />
        <EnterpriseTrust />
        <Pricing />
      </main>
      <SiteFooter />
    </div>
  )
}
