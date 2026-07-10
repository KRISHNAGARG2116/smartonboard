import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { GoogleOAuthProvider } from '@react-oauth/google'
import './index.css'
import './globals.css'
import App from './App.tsx'

const googleClientId = import.meta.env.VITE_GOOGLE_CLIENT_ID || 'mock-google-client-id'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <GoogleOAuthProvider clientId={googleClientId}>
      <App />
    </GoogleOAuthProvider>
  </StrictMode>,
)

// Native browser Core Web Vitals observer
function logWebVitals() {
  if (typeof window === 'undefined') return
  try {
    const fcpObserver = new PerformanceObserver((list) => {
      for (const entry of list.getEntries()) {
        console.log(`[Web Vitals] FCP: ${entry.startTime.toFixed(1)}ms`)
      }
    })
    fcpObserver.observe({ type: 'paint', buffered: true })

    const lcpObserver = new PerformanceObserver((list) => {
      const entries = list.getEntries()
      const lastEntry = entries[entries.length - 1]
      console.log(`[Web Vitals] LCP: ${lastEntry.startTime.toFixed(1)}ms`)
    })
    lcpObserver.observe({ type: 'largest-contentful-paint', buffered: true })

    let clsValue = 0
    const clsObserver = new PerformanceObserver((list) => {
      for (const entry of list.getEntries() as any[]) {
        if (!entry.hadRecentInput) {
          clsValue += entry.value
          console.log(`[Web Vitals] CLS: Cumulative Layout Shift is ${clsValue.toFixed(4)}`)
        }
      }
    })
    clsObserver.observe({ type: 'layout-shift', buffered: true })
  } catch (e) {
    console.warn('PerformanceObserver not supported:', e)
  }
}

logWebVitals()
