import { motion } from 'framer-motion'
import { type ReactNode } from 'react'

interface AnimatedPageProps {
  children: ReactNode
}

export default function AnimatedPage({ children }: AnimatedPageProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      transition={{ duration: 0.25, ease: 'easeOut' as any }}
    >
      {children}
    </motion.div>
  )
}
