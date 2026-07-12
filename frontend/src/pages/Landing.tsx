import { SiteHeader } from '../components/landing/site-header'
import { Hero } from '../components/landing/hero'
import { RecruiterDashboard } from '../components/landing/recruiter-dashboard'
import { EmmaApplies } from '../components/landing/emma-applies'
import { HiringWorkspace } from '../components/landing/hiring-workspace'
import { BusinessOutcomes } from '../components/landing/business-outcomes'
import { EnterpriseTrust } from '../components/landing/enterprise-trust'
import { Pricing } from '../components/landing/pricing'
import { SiteFooter } from '../components/landing/site-footer'
import { BlueprintGrid } from '../components/landing/blueprint-grid'
import { StoryConnector } from '../components/landing/story-connector'

export default function Landing() {
  return (
    <div className="landing-blueprint-page min-h-screen bg-transparent font-sans">
      <BlueprintGrid />
      <SiteHeader />
      <StoryConnector />
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
