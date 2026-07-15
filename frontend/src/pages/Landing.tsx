import { motion } from 'motion/react'
import { Hero } from '../components/landing/hero'
import { RecruiterDashboard } from '../components/landing/recruiter-dashboard'
import { EmmaApplies } from '../components/landing/emma-applies'
import { HiringWorkspace } from '../components/landing/hiring-workspace'
import { BusinessOutcomes } from '../components/landing/business-outcomes'
import { EnterpriseTrust } from '../components/landing/enterprise-trust'
import { Capabilities } from '../components/landing/pricing'
import { BlueprintGrid } from '../components/landing/blueprint-grid'
import { SiteHeader } from '../components/landing/site-header'
import { StoryConnector } from '../components/landing/story-connector'
import { SiteFooter } from '../components/landing/site-footer'

export default function Landing() {
  return (
    <div className="relative min-h-screen bg-[#faf7f2] font-sans selection:bg-[#4a1f2c]/10 selection:text-[#4a1f2c]">
      <BlueprintGrid />
      <SiteHeader />
      <StoryConnector />
      <main className="space-y-6 md:space-y-10 lg:space-y-12 py-8 md:py-12">
        <motion.div
          initial={{ opacity: 0.3, y: 30, scale: 0.97 }}
          whileInView={{ opacity: 1, y: 0, scale: 1 }}
          viewport={{ once: false, amount: 0.2, margin: "-12% 0px -12% 0px" }}
          transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
          className="mx-auto w-[92vw] lg:w-[90vw] max-w-[1440px] border border-[#e4d9ce] rounded-[24px] md:rounded-[32px] bg-[#faf7f2] shadow-soft relative z-10 min-h-[75vh] lg:min-h-[85vh] flex flex-col justify-center py-6 md:py-10 lg:py-14"
        >
          <Hero />
        </motion.div>
        <motion.div
          initial={{ opacity: 0.3, y: 30, scale: 0.97 }}
          whileInView={{ opacity: 1, y: 0, scale: 1 }}
          viewport={{ once: false, amount: 0.2, margin: "-12% 0px -12% 0px" }}
          transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
          className="mx-auto w-[92vw] lg:w-[90vw] max-w-[1440px] border border-[#e4d9ce] rounded-[24px] md:rounded-[32px] bg-[#faf7f2] shadow-soft relative z-10 min-h-[75vh] lg:min-h-[85vh] flex flex-col justify-center py-6 md:py-10 lg:py-14"
          id="product"
        >
          <RecruiterDashboard />
        </motion.div>
        <motion.div
          initial={{ opacity: 0.3, y: 30, scale: 0.97 }}
          whileInView={{ opacity: 1, y: 0, scale: 1 }}
          viewport={{ once: false, amount: 0.2, margin: "-12% 0px -12% 0px" }}
          transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
          className="mx-auto w-[92vw] lg:w-[90vw] max-w-[1440px] border border-[#e4d9ce] rounded-[24px] md:rounded-[32px] bg-[#faf7f2] shadow-soft relative z-10 min-h-[75vh] lg:min-h-[85vh] flex flex-col justify-center py-6 md:py-10 lg:py-14"
        >
          <EmmaApplies />
        </motion.div>
        <motion.div
          initial={{ opacity: 0.3, y: 30, scale: 0.97 }}
          whileInView={{ opacity: 1, y: 0, scale: 1 }}
          viewport={{ once: false, amount: 0.2, margin: "-12% 0px -12% 0px" }}
          transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
          className="mx-auto w-[92vw] lg:w-[90vw] max-w-[1440px] border border-[#e4d9ce] rounded-[24px] md:rounded-[32px] bg-[#faf7f2] shadow-soft relative z-10 min-h-[75vh] lg:min-h-[85vh] flex flex-col justify-center py-6 md:py-10 lg:py-14"
          id="workspace"
        >
          <HiringWorkspace />
        </motion.div>
        <motion.div
          initial={{ opacity: 0.3, y: 30, scale: 0.97 }}
          whileInView={{ opacity: 1, y: 0, scale: 1 }}
          viewport={{ once: false, amount: 0.2, margin: "-12% 0px -12% 0px" }}
          transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
          className="mx-auto w-[92vw] lg:w-[90vw] max-w-[1440px] border border-[#e4d9ce] rounded-[24px] md:rounded-[32px] bg-[#faf7f2] shadow-soft relative z-10 min-h-[75vh] lg:min-h-[85vh] flex flex-col justify-center py-6 md:py-10 lg:py-14"
          id="outcomes"
        >
          <BusinessOutcomes />
        </motion.div>
        <motion.div
          initial={{ opacity: 0.3, y: 30, scale: 0.97 }}
          whileInView={{ opacity: 1, y: 0, scale: 1 }}
          viewport={{ once: false, amount: 0.2, margin: "-12% 0px -12% 0px" }}
          transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
          className="mx-auto w-[92vw] lg:w-[90vw] max-w-[1440px] border border-[#e4d9ce] rounded-[24px] md:rounded-[32px] bg-[#faf7f2] shadow-soft relative z-10 min-h-[75vh] lg:min-h-[85vh] flex flex-col justify-center py-6 md:py-10 lg:py-14"
          id="enterprise"
        >
          <EnterpriseTrust />
        </motion.div>
        <motion.div
          initial={{ opacity: 0.3, y: 30, scale: 0.97 }}
          whileInView={{ opacity: 1, y: 0, scale: 1 }}
          viewport={{ once: false, amount: 0.2, margin: "-12% 0px -12% 0px" }}
          transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
          className="mx-auto w-[92vw] lg:w-[90vw] max-w-[1440px] border border-[#e4d9ce] rounded-[24px] md:rounded-[32px] bg-[#faf7f2] shadow-soft relative z-10 min-h-[75vh] lg:min-h-[85vh] flex flex-col justify-center py-6 md:py-10 lg:py-14"
          id="pricing"
        >
          <Capabilities />
        </motion.div>
      </main>
      <SiteFooter />
    </div>
  )
}
