import { createContext, useContext, useEffect, useMemo, type ReactNode } from 'react'

interface ThemeContextValue {
  theme: 'light'
  resolvedTheme: 'light'
  toggleTheme: () => void
  setTheme: (theme: 'light') => void
}

const ThemeContext = createContext<ThemeContextValue | null>(null)

export function ThemeProvider({ children }: { children: ReactNode }) {
  useEffect(() => {
    // Force data-theme to light globally
    document.documentElement.setAttribute('data-theme', 'light')
    document.documentElement.style.colorScheme = 'light'
    
    // Remove any dark mode classes from body
    document.body.classList.remove('theme-purple-dream')
    
    // Clear legacy theme selections to avoid local storage confusion
    localStorage.removeItem('smartonboard-theme')
  }, [])

  const value = useMemo<ThemeContextValue>(() => ({
    theme: 'light',
    resolvedTheme: 'light',
    toggleTheme: () => {
      // Steep is daylight-only. Toggling is a no-op.
    },
    setTheme: () => {
      // Steep is daylight-only. Setting is a no-op.
    }
  }), [])

  return (
    <ThemeContext.Provider value={value}>
      {children}
    </ThemeContext.Provider>
  )
}

export function useTheme() {
  const ctx = useContext(ThemeContext)
  if (!ctx) throw new Error('useTheme must be used within ThemeProvider')
  return ctx
}
