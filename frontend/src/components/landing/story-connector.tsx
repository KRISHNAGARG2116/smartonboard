import { useEffect, useState } from 'react'
import './story-connector.css'

const CHAPTERS = ['product', 'workspace', 'outcomes', 'enterprise', 'pricing']

export function StoryConnector() {
  const [active, setActive] = useState(0)
  useEffect(() => {
    const sections = CHAPTERS.map((id) => document.getElementById(id)).filter((section): section is HTMLElement => Boolean(section))
    const observer = new IntersectionObserver((entries) => entries.forEach((entry) => { if (entry.isIntersecting) setActive(Math.max(0, CHAPTERS.indexOf(entry.target.id))) }), { rootMargin: '-45% 0px -45% 0px', threshold: 0 })
    sections.forEach((section) => observer.observe(section))
    return () => observer.disconnect()
  }, [])
  return <div className="story-connector" aria-hidden="true"><div className="story-connector-ring" style={{ transform: `rotate(${active * 72}deg)` }}>{CHAPTERS.map((chapter, index) => <i key={chapter} data-active={index === active} style={{ transform: `rotate(${index * 72}deg) translateY(-2.75rem)` }} />)}</div><span>{String(active + 1).padStart(2, '0')}</span></div>
}
