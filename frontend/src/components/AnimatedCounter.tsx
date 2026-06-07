import { useEffect, useRef, useState } from 'react'
import { animate, useInView } from 'framer-motion'

interface AnimatedCounterProps {
  value: number | string
}

export default function AnimatedCounter({ value }: AnimatedCounterProps) {
  const ref = useRef<HTMLSpanElement>(null)
  const isInView = useInView(ref, { once: true, margin: '0px 0px -50px 0px' })
  const [displayValue, setDisplayValue] = useState<string>('0')

  // Parse value and extract number + suffix
  let numericValue = 0
  let suffix = ''
  let isNumeric = false

  if (typeof value === 'number') {
    numericValue = value
    isNumeric = true
  } else if (typeof value === 'string') {
    // E.g. "98.5%", "12 days", "N/A"
    const match = value.trim().match(/^([\d.]+)\s*(.*)$/)
    if (match) {
      const parsed = parseFloat(match[1])
      if (!isNaN(parsed)) {
        numericValue = parsed
        suffix = match[2] || ''
        isNumeric = true
      }
    } else {
      const matchLeadingPercent = value.trim().match(/^(.*?)\s*([\d.]+)$/)
      if (matchLeadingPercent) {
        const parsed = parseFloat(matchLeadingPercent[2])
        if (!isNaN(parsed)) {
          numericValue = parsed
          suffix = matchLeadingPercent[1] || ''
          isNumeric = true
        }
      }
    }
  }

  useEffect(() => {
    if (!isInView || !isNumeric) {
      if (!isNumeric) {
        setDisplayValue(String(value))
      }
      return
    }

    const controls = animate(0, numericValue, {
      duration: 0.8,
      ease: 'easeOut',
      onUpdate(val) {
        const formatted = numericValue % 1 === 0
          ? Math.round(val).toString()
          : val.toFixed(1)
        
        if (value.toString().trim().startsWith(suffix) && suffix) {
          setDisplayValue(`${suffix}${formatted}`)
        } else {
          setDisplayValue(`${formatted}${suffix}`)
        }
      }
    })

    return () => controls.stop()
  }, [numericValue, isInView, isNumeric, value, suffix])

  if (!isNumeric) {
    return <span ref={ref}>{String(value)}</span>
  }

  return <span ref={ref}>{displayValue}</span>
}
