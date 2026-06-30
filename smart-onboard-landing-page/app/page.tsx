import { SiteHeader } from '@/components/site-header'
import { Hero } from '@/components/hero'
import { RecruiterDashboard } from '@/components/recruiter-dashboard'
import { EmmaApplies } from '@/components/emma-applies'
import { HiringWorkspace } from '@/components/hiring-workspace'
import { BusinessOutcomes } from '@/components/business-outcomes'
import { EnterpriseTrust } from '@/components/enterprise-trust'
import { Pricing } from '@/components/pricing'
import { SiteFooter } from '@/components/site-footer'

export default function Page() {
  return (
    <div className="min-h-screen bg-background">
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
