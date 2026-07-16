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
  const [isPinned, setIsPinned] = useState(false)
  const [activeIndex, setActiveIndex] = useState(0)

  const lastScrollY = useRef(0)
  const hasCompleted = useRef(false)
  const cooldown = useRef(false)
  const touchStartY = useRef(0)

  // Snap and Pin detection
  useEffect(() => {
    const handleScrollCheck = () => {
      const section = sectionRef.current
      if (!section) return

      const rect = section.getBoundingClientRect()
      const currentScrollY = window.scrollY
      const direction = currentScrollY > lastScrollY.current ? 'down' : 'up'
      lastScrollY.current = currentScrollY

      const sectionCenter = rect.top + rect.height / 2
      const viewportCenter = window.innerHeight / 2
      const distanceToCenter = Math.abs(sectionCenter - viewportCenter)

      // Reset completed status if the user scrolls back past the top of the section
      if (rect.top > window.innerHeight) {
        hasCompleted.current = false
      }

      // Pin ONLY when scrolling down (forward navigation)
      if (window.innerWidth >= 1024 && direction === 'down' && !isPinned && !hasCompleted.current) {
        // When the section center is getting close to the viewport center
        if (rect.top > 0 && rect.top < window.innerHeight * 0.4 && distanceToCenter < 120) {
          // Snap scroll position to center
          const targetScrollY = currentScrollY + rect.top - (window.innerHeight - rect.height) / 2
          window.scrollTo({ top: targetScrollY, behavior: 'instant' })
          setIsPinned(true)
          setActiveIndex(0)
        }
      }
    }

    window.addEventListener('scroll', handleScrollCheck, { passive: true })
    return () => window.removeEventListener('scroll', handleScrollCheck)
  }, [isPinned])

  const pinnedScrollY = useRef(0)

  // Body scroll lock state coordinator & absolute centering lock
  useEffect(() => {
    if (isPinned) {
      const section = sectionRef.current
      if (section) {
        const rect = section.getBoundingClientRect()
        const currentScrollY = window.scrollY
        pinnedScrollY.current = currentScrollY + rect.top - (window.innerHeight - rect.height) / 2
        window.scrollTo({ top: pinnedScrollY.current, behavior: 'instant' })
      }

      const scrollbarWidth = window.innerWidth - document.documentElement.clientWidth
      document.body.style.overflow = 'hidden'
      if (scrollbarWidth > 0) {
        document.body.style.paddingRight = `${scrollbarWidth}px`
      }

      const forceCenterScroll = () => {
        if (Math.abs(window.scrollY - pinnedScrollY.current) > 0.5) {
          window.scrollTo(0, pinnedScrollY.current)
        }
      }

      window.addEventListener('scroll', forceCenterScroll, { passive: false })
      return () => {
        window.removeEventListener('scroll', forceCenterScroll)
        document.body.style.overflow = ''
        document.body.style.paddingRight = ''
      }
    } else {
      document.body.style.overflow = ''
      document.body.style.paddingRight = ''
    }
  }, [isPinned])

  // Stage transition scroll interceptor
  useEffect(() => {
    if (!isPinned) return

    const handleWheel = (e: WheelEvent) => {
      e.preventDefault()

      if (cooldown.current) return

      const direction = e.deltaY > 0 ? 'down' : 'up'
      if (direction === 'down') {
        if (activeIndex < WORKFLOW_STAGES.length - 1) {
          setActiveIndex((prev) => prev + 1)
          triggerCooldown()
        } else {
          setIsPinned(false)
          hasCompleted.current = true
          triggerCooldown()
        }
      } else {
        if (activeIndex > 0) {
          setActiveIndex((prev) => prev - 1)
          triggerCooldown()
        } else {
          setIsPinned(false)
          hasCompleted.current = false
          triggerCooldown()
        }
      }
    }

    const handleTouchStart = (e: TouchEvent) => {
      touchStartY.current = e.touches[0].clientY
    }

    const handleTouchMove = (e: TouchEvent) => {
      e.preventDefault()

      if (cooldown.current) return

      const currentY = e.touches[0].clientY
      const diffY = touchStartY.current - currentY

      if (Math.abs(diffY) < 15) return

      const direction = diffY > 0 ? 'down' : 'up'
      if (direction === 'down') {
        if (activeIndex < WORKFLOW_STAGES.length - 1) {
          setActiveIndex((prev) => prev + 1)
          touchStartY.current = currentY
          triggerCooldown()
        } else {
          setIsPinned(false)
          hasCompleted.current = true
          triggerCooldown()
        }
      } else {
        if (activeIndex > 0) {
          setActiveIndex((prev) => prev - 1)
          touchStartY.current = currentY
          triggerCooldown()
        } else {
          setIsPinned(false)
          hasCompleted.current = false
          triggerCooldown()
        }
      }
    }

    const handleKeyDown = (e: KeyboardEvent) => {
      const keys = ['ArrowDown', 'ArrowUp', ' ', 'PageDown', 'PageUp']
      if (!keys.includes(e.key)) return

      e.preventDefault()

      if (cooldown.current) return

      if (e.key === 'ArrowDown' || e.key === ' ' || e.key === 'PageDown') {
        if (activeIndex < WORKFLOW_STAGES.length - 1) {
          setActiveIndex((prev) => prev + 1)
          triggerCooldown()
        } else {
          setIsPinned(false)
          hasCompleted.current = true
          triggerCooldown()
        }
      } else if (e.key === 'ArrowUp' || e.key === 'PageUp') {
        if (activeIndex > 0) {
          setActiveIndex((prev) => prev - 1)
          triggerCooldown()
        } else {
          setIsPinned(false)
          hasCompleted.current = false
          triggerCooldown()
        }
      }
    }

    const triggerCooldown = () => {
      cooldown.current = true
      setTimeout(() => {
        cooldown.current = false
      }, 500)
    }

    window.addEventListener('wheel', handleWheel, { passive: false, capture: true })
    window.addEventListener('touchstart', handleTouchStart, { passive: true })
    window.addEventListener('touchmove', handleTouchMove, { passive: false, capture: true })
    window.addEventListener('keydown', handleKeyDown, { passive: false, capture: true })

    return () => {
      window.removeEventListener('wheel', handleWheel, { capture: true })
      window.removeEventListener('touchstart', handleTouchStart)
      window.removeEventListener('touchmove', handleTouchMove, { capture: true })
      window.removeEventListener('keydown', handleKeyDown, { capture: true })
    }
  }, [isPinned, activeIndex])

  const activeStage = WORKFLOW_STAGES[activeIndex]
  const workflowStyle = { '--workflow-progress': activeIndex } as CSSProperties

  return (
    <section ref={sectionRef} className="workflow-section relative flex flex-col items-center justify-start bg-transparent py-10 md:py-14" aria-labelledby="workflow-title">
      <div className="workflow-scroll-space w-full mx-auto px-6 grid grid-cols-1 lg:grid-cols-[1.1fr_1.9fr] gap-8 items-center justify-between">
        {/* Left Column: Heading & Text */}
        <div className="text-left max-w-xl mb-4 lg:mb-0 lg:sticky lg:top-[35%] lg:pr-6">
          <SectionLabel>A considered hiring workflow</SectionLabel>
          <h2 id="workflow-title" className="mt-3 text-balance font-heading text-4xl leading-tight text-[#1f090b] md:text-5xl">
            The system keeps moving.<br />Your team stays in control.
          </h2>
        </div>

        {/* Sticky viewport area for circular orbit */}
        <div className="workflow-sticky w-full flex items-center justify-center relative min-h-[550px] md:min-h-[580px] overflow-visible" style={workflowStyle}>
          
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

          <p className="workflow-progress" aria-hidden="true">
            {isPinned ? `STAGE ${activeIndex + 1} OF ${WORKFLOW_STAGES.length} · SCROLL TO ADVANCE` : 'SCROLL TO FOLLOW THE FLOW'}
          </p>
        </div>
      </div>

      {/* Mobile Explainer List */}
      <div className="w-full max-w-xl px-6 lg:hidden">
        <ol className="workflow-mobile-list mt-8 w-full">
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
