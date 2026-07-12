import { useEffect, useRef, useState, type CSSProperties } from 'react'
import {
  Bot, BriefcaseBusiness, CalendarCheck, ClipboardCheck, FileSearch,
  Handshake, ScanSearch, Send, Sparkles, UsersRound,
} from 'lucide-react'
import { SectionLabel } from './primitives'
import './hiring-workspace.css'

const WORKFLOW_STAGES = [
  { title: 'Create job', description: 'Set the role, team context, and the outcomes that matter.', icon: BriefcaseBusiness },
  { title: 'AI job writer', description: 'A structured first draft gives the team a clear, consistent starting point.', icon: Sparkles },
  { title: 'Publish position', description: 'Share a trusted opportunity with the right candidate audience.', icon: Send },
  { title: 'Candidates apply', description: 'Verified people apply with the resume that best represents their experience.', icon: UsersRound },
  { title: 'AI resume screening', description: 'Skills and experience are organized into an evidence-led review.', icon: FileSearch },
  { title: 'Candidate matching', description: 'Relevance signals help recruiters focus their attention with context.', icon: ScanSearch },
  { title: 'Talent CRM review', description: 'Your team examines the full pool and makes every decision.', icon: ClipboardCheck },
  { title: 'Interview scheduling', description: 'Prepare the team with focused context and a shared interview plan.', icon: CalendarCheck },
  { title: 'AI interview assistant', description: 'Prepare focused questions and clearer interview context—without automating the decision.', icon: Bot },
  { title: 'Hiring analytics', description: 'Bring evidence, interviews, and team judgment together in one place.', icon: ScanSearch },
  { title: 'Offer accepted', description: 'Close the hiring loop with a confident, documented outcome.', icon: Handshake },
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
    <section id="workspace" ref={sectionRef} className="workflow-section" aria-labelledby="workflow-title">
      <div className="workflow-scroll-space">
        <div className="workflow-sticky" style={workflowStyle}>
          <div className="workflow-copy">
            <SectionLabel>A considered hiring workflow</SectionLabel>
            <h2 id="workflow-title" className="mt-5 text-balance font-heading text-4xl leading-tight text-foreground md:text-5xl">
              The system keeps moving. Your team stays in control.
            </h2>
            <p className="mt-4 max-w-xl text-pretty text-[16px] leading-relaxed text-muted-foreground">
              SmartOnboard brings trusted signals and AI assistance into every stage, while recruiters retain the final say.
            </p>
          </div>

          <div className="workflow-orbit" aria-live="polite" aria-atomic="true">
            <div className="workflow-center"><span>Trusted signals.<br />Human decisions.</span></div>
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

          <article className="workflow-stage-card" key={activeStage.title}>
            <p>Stage {String(activeIndex + 1).padStart(2, '0')} of {String(WORKFLOW_STAGES.length).padStart(2, '0')}</p>
            <h3>{activeStage.title}</h3>
            <p>{activeStage.description}</p>
          </article>
          <p className="workflow-progress" aria-hidden="true">SCROLL TO FOLLOW THE FLOW</p>

          <ol className="workflow-mobile-list">
            {WORKFLOW_STAGES.map((stage) => {
              const Icon = stage.icon
              return <li key={stage.title} className="workflow-mobile-item"><span className="workflow-mobile-icon"><Icon aria-hidden="true" strokeWidth={1.7} /></span><div><h3>{stage.title}</h3><p>{stage.description}</p></div></li>
            })}
          </ol>
        </div>
      </div>
    </section>
  )
}
