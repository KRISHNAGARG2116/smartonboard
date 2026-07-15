import { useEffect, useMemo, useRef, type RefObject, type ReactNode } from 'react'
import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'

import './ScrollFloat.css'

gsap.registerPlugin(ScrollTrigger)

interface ScrollFloatProps {
  children: ReactNode
  scrollContainerRef?: RefObject<HTMLElement | null>
  containerClassName?: string
  textClassName?: string
  animationDuration?: number
  ease?: string
  scrollStart?: string
  scrollEnd?: string
  stagger?: number
}

export function ScrollFloat({
  children,
  scrollContainerRef,
  containerClassName = '',
  textClassName = '',
  animationDuration = 0.8,
  ease = 'power2.out',
  scrollStart = 'top bottom-=8%',
  scrollEnd = 'bottom top+=8%',
  stagger = 0.015,
}: ScrollFloatProps) {
  const containerRef = useRef<HTMLHeadingElement>(null)

  // Group characters into words to allow correct browser line wrapping,
  // preventing characters from wrapping individually inside words.
  const splitText = useMemo(() => {
    const text = typeof children === 'string' ? children : ''
    const words = text.split(' ')
    const elements: ReactNode[] = []

    words.forEach((word, wordIndex) => {
      elements.push(
        <span key={`w-${wordIndex}`} className="word inline-block whitespace-nowrap">
          {word.split('').map((char, charIndex) => (
            <span className="char inline-block" key={charIndex}>
              {char}
            </span>
          ))}
        </span>
      )
      if (wordIndex < words.length - 1) {
        elements.push(' ')
      }
    })

    return elements
  }, [children])

  useEffect(() => {
    const el = containerRef.current
    if (!el) return

    const scroller = scrollContainerRef && scrollContainerRef.current ? scrollContainerRef.current : window
    const charElements = el.querySelectorAll('.char')

    const anim = gsap.fromTo(
      charElements,
      {
        willChange: 'opacity, transform',
        opacity: 0,
        yPercent: 40,
        scaleY: 1.1,
        scaleX: 0.98,
        transformOrigin: '50% 0%',
      },
      {
        duration: animationDuration,
        ease: ease,
        opacity: 1,
        yPercent: 0,
        scaleY: 1,
        scaleX: 1,
        stagger: stagger,
        scrollTrigger: {
          trigger: el,
          scroller,
          start: scrollStart,
          end: scrollEnd,
          toggleActions: 'play none none reverse',
        },
      }
    )

    return () => {
      anim.kill()
    }
  }, [scrollContainerRef, animationDuration, ease, scrollStart, scrollEnd, stagger])

  // Combine container and typography classes directly on the outer heading
  // to preserve exact original layout wrapping and formatting rules.
  return (
    <h2 ref={containerRef} className={`scroll-float ${containerClassName} ${textClassName}`}>
      <span className="scroll-float-text">{splitText}</span>
    </h2>
  )
}

export default ScrollFloat
