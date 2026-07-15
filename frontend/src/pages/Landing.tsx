import { SiteHeader } from '../components/landing/site-header'
import { Hero } from '../components/landing/hero'
import { RecruiterDashboard } from '../components/landing/recruiter-dashboard'
import { EmmaApplies } from '../components/landing/emma-applies'
import { HiringWorkspace } from '../components/landing/hiring-workspace'
import { BusinessOutcomes } from '../components/landing/business-outcomes'
import { EnterpriseTrust } from '../components/landing/enterprise-trust'
import { Capabilities } from '../components/landing/pricing'
import { SiteFooter } from '../components/landing/site-footer'
import { BlueprintGrid } from '../components/landing/blueprint-grid'
import { StoryConnector } from '../components/landing/story-connector'

export default function Landing() {
  return (
    <div className="landing-blueprint-page min-h-screen bg-transparent font-sans">
      <BlueprintGrid />
      <SiteHeader />
      <StoryConnector />
      <main className="space-y-4 md:space-y-6 py-4 md:py-6">
        <div className="mx-auto w-[92vw] lg:w-[90vw] max-w-[1440px] border border-[#e4d9ce] rounded-[24px] md:rounded-[32px] bg-[#faf7f2] shadow-soft relative z-10">
          <Hero />
        </div>
        <div className="mx-auto w-[92vw] lg:w-[90vw] max-w-[1440px] border border-[#e4d9ce] rounded-[24px] md:rounded-[32px] bg-[#faf7f2] shadow-soft relative z-10" id="product">
          <RecruiterDashboard />
        </div>
        <div className="mx-auto w-[92vw] lg:w-[90vw] max-w-[1440px] border border-[#e4d9ce] rounded-[24px] md:rounded-[32px] bg-[#faf7f2] shadow-soft relative z-10">
          <EmmaApplies />
        </div>
        <div className="mx-auto w-[92vw] lg:w-[90vw] max-w-[1440px] border border-[#e4d9ce] rounded-[24px] md:rounded-[32px] bg-[#faf7f2] shadow-soft relative z-10" id="workspace">
          <HiringWorkspace />
        </div>
        <div className="mx-auto w-[92vw] lg:w-[90vw] max-w-[1440px] border border-[#e4d9ce] rounded-[24px] md:rounded-[32px] bg-[#faf7f2] shadow-soft relative z-10" id="outcomes">
          <BusinessOutcomes />
        </div>
        <div className="mx-auto w-[92vw] lg:w-[90vw] max-w-[1440px] border border-[#e4d9ce] rounded-[24px] md:rounded-[32px] bg-[#faf7f2] shadow-soft relative z-10" id="enterprise">
          <EnterpriseTrust />
        </div>
        <div className="mx-auto w-[92vw] lg:w-[90vw] max-w-[1440px] border border-[#e4d9ce] rounded-[24px] md:rounded-[32px] bg-[#faf7f2] shadow-soft relative z-10" id="pricing">
          <Capabilities />
        </div>
      </main>
      <SiteFooter />
    </div>
  )
}
