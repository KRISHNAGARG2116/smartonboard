import { useEffect, useRef, useState, type CSSProperties } from 'react'
import {
  BriefcaseBusiness, CalendarCheck, ClipboardCheck, FileSearch,
  Handshake, ScanSearch, Send, Sparkles, UsersRound,
} from 'lucide-react'
import { SectionLabel } from './primitives'
import './hiring-workspace.css'

const WORKFLOW_STAGES = [
  {
    title: 'Create job',
    description: 'Define roles, team goals, and critical hiring parameters.',
    benefit: 'Saves 4+ hours of alignment',
    icon: BriefcaseBusiness,
  },
  {
    title: 'AI job writer',
    description: 'Generate consistent and clear role descriptions automatically.',
    benefit: 'Standardizes target profiles',
    icon: Sparkles,
  },
  {
    title: 'Publish position',
    description: 'Distribute job postings to high-signal candidate channels.',
    benefit: 'Maximizes target reach',
    icon: Send,
  },
  {
    title: 'Verify candidates',
    description: 'Twilio SMS and email OTP identity validation on application.',
    benefit: 'Eliminates fake profiles',
    icon: UsersRound,
  },
  {
    title: 'AI resume screening',
    description: 'Parse, verify, and match resume skills to the role brief.',
    benefit: 'Cuts manual filtering by 90%',
    icon: FileSearch,
  },
  {
    title: 'Candidate matching',
    description: 'Instant applicability scoring visible to recruiters.',
    benefit: 'Highlights best fits instantly',
    icon: ScanSearch,
  },
  {
    title: 'CRM review',
    description: 'Recruiters review complete profiles, notes, and signals.',
    benefit: 'Ensures human final decision',
    icon: ClipboardCheck,
  },
  {
    title: 'Focused interviews',
    description: 'Schedule, coordinate, and align team interview plans.',
    benefit: 'Accelerates feedback loop',
    icon: CalendarCheck,
  },
  {
    title: 'Outcome analytics',
    description: 'Consolidated executive view of team performance and pipeline.',
    benefit: 'Predictable hiring targets',
    icon: ScanSearch,
  },
  {
    title: 'Offer accepted',
    description: 'Confidently close candidate matching in one workspace.',
    benefit: 'Saves 35% time-to-hire',
    icon: Handshake,
  },
] as const

export function HiringWorkspace() {
  const sectionRef = useRef<HTMLElement>(null)
  const frameRef = useRef<number | undefined>(undefined)
  const [progress, setProgress] = useState(0)
  const [activeIndex, setActiveIndex] = useState(0)

  useEffect(() => {
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    if (reducedMotion) return

    const update = () => {
      frameRef.current = undefined
      const section = sectionRef.current
      if (!section) return
      const rect = section.getBoundingClientRect()
      const scrollableDistance = Math.max(section.offsetHeight - window.innerHeight, 1)
      const nextProgress = Math.min(1, Math.max(0, -rect.top / scrollableDistance))
      setProgress(nextProgress)
      setActiveIndex(Math.min(WORKFLOW_STAGES.length - 1, Math.round(nextProgress * (WORKFLOW_STAGES.length - 1))))
    }
    const onScroll = () => {
      if (!frameRef.current) frameRef.current = window.requestAnimationFrame(update)
    }
    update()
    window.addEventListener('scroll', onScroll, { passive: true })
    window.addEventListener('resize', onScroll)
    return () => {
      window.removeEventListener('scroll', onScroll)
      window.removeEventListener('resize', onScroll)
      if (frameRef.current) window.cancelAnimationFrame(frameRef.current)
    }
  }, [])

  const activeStage = WORKFLOW_STAGES[activeIndex]
  const workflowStyle = { '--workflow-progress': progress } as CSSProperties

  return (
    <section ref={sectionRef} className="workflow-section relative flex flex-col items-center justify-start bg-transparent py-20" aria-labelledby="workflow-title">
      <div className="workflow-scroll-space w-full max-w-6xl mx-auto px-6 flex flex-col items-center">
        {/* Top Header */}
        <div className="text-center max-w-2xl mb-8">
          <SectionLabel className="justify-center">A considered hiring workflow</SectionLabel>
          <h2 id="workflow-title" className="mt-5 text-balance font-heading text-4xl leading-tight text-[#1f090b] md:text-5xl">
            The system keeps moving.<br />Your team stays in control.
          </h2>
        </div>

        {/* Sticky viewport area for circular orbit */}
        <div className="workflow-sticky w-full flex items-center justify-center relative min-h-[600px] md:min-h-[650px] overflow-visible" style={workflowStyle}>
          
          {/* Centered Orbit */}
          <div className="workflow-orbit relative" aria-live="polite" aria-atomic="true">
            
            {/* Center Circle showing Active Stage */}
            <div className="workflow-center flex flex-col items-center justify-center p-6 text-center">
              <span className="text-[10px] tracking-[0.15em] font-bold text-[#4a1f2c] uppercase">
                Stage {String(activeIndex + 1).padStart(2, '0')}
              </span>
              <h3 className="mt-2 font-heading text-lg md:text-xl text-[#1f090b] font-bold">
                {activeStage.title}
              </h3>
              <p className="mt-2.5 text-[12.5px] leading-relaxed text-zinc-600 font-medium max-w-[210px] mx-auto">
                {activeStage.description}
              </p>
              <div className="mt-3.5 inline-flex items-center gap-1.5 rounded-full bg-[#3c5e43]/10 px-3 py-1 text-[11px] font-bold text-[#3c5e43]">
                {activeStage.benefit}
              </div>
            </div>

            {/* Orbit nodes */}
            {WORKFLOW_STAGES.map((stage, index) => {
              const Icon = stage.icon
              const angle = `${(index / WORKFLOW_STAGES.length) * 360 - 90}deg`
              return (
                <button
                  key={stage.title}
                  type="button"
                  className="workflow-node"
                  style={{ '--node-angle': angle } as CSSProperties}
                  data-active={index === activeIndex}
                  aria-label={`Stage ${index + 1}: ${stage.title}`}
                  aria-pressed={index === activeIndex}
                  onClick={() => setActiveIndex(index)}
                >
                  <Icon aria-hidden="true" strokeWidth={1.7} />
                </button>
              )
            })}
          </div>

          <p className="workflow-progress" aria-hidden="true">SCROLL TO FOLLOW THE FLOW</p>
        </div>

        {/* Mobile Explainer List */}
        <ol className="workflow-mobile-list mt-8 w-full max-w-xl">
          {WORKFLOW_STAGES.map((stage, index) => {
            const Icon = stage.icon
            return (
              <li key={stage.title} className="workflow-mobile-item">
                <span className="workflow-mobile-icon"><Icon aria-hidden="true" strokeWidth={1.7} /></span>
                <div>
                  <span className="text-[9px] font-bold text-[#4a1f2c] tracking-wider uppercase">Stage {index + 1}</span>
                  <h3 className="text-[15px] font-bold text-[#1f090b] mt-0.5">{stage.title}</h3>
                  <p className="text-[13px] text-zinc-600 mt-1 font-medium">{stage.description}</p>
                  <div className="mt-2 inline-flex items-center gap-1 rounded-full bg-[#3c5e43]/8 px-2.5 py-0.5 text-[11px] font-semibold text-[#3c5e43]">
                    {stage.benefit}
                  </div>
                </div>
              </li>
            )
          })}
        </ol>
      </div>
    </section>
  )
}
