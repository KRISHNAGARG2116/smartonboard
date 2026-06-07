import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { useAuth } from './AuthContext'

export type Theme = 'light' | 'dark' | 'system'

interface ThemeContextValue {
  theme: Theme
  resolvedTheme: 'light' | 'dark'
  toggleTheme: () => void
  setTheme: (theme: Theme) => void
}

const ThemeContext = createContext<ThemeContextValue | null>(null)

export function ThemeProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth()
  
  const [theme, setThemeState] = useState<Theme>(() => {
    const saved = localStorage.getItem('smartonboard-theme')
    if (saved === 'light' || saved === 'dark' || saved === 'system') {
      return saved
    }
    return 'system' // Default is System to respect OS theme on first visit
  })

  const [resolvedTheme, setResolvedTheme] = useState<'light' | 'dark'>(() => {
    const saved = localStorage.getItem('smartonboard-theme')
    if (saved === 'light' || saved === 'dark') {
      return saved
    }
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
  })

  // Sync theme when user state changes (e.g. login)
  useEffect(() => {
    if (user) {
      const userSaved = localStorage.getItem(`smartonboard-theme-${user.id}`)
      if (userSaved === 'light' || userSaved === 'dark' || userSaved === 'system') {
        setThemeState(userSaved)
      }
    }
  }, [user])

  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
    
    const applyTheme = () => {
      let currentResolved: 'light' | 'dark'
      if (theme === 'system') {
        currentResolved = mediaQuery.matches ? 'dark' : 'light'
      } else {
        currentResolved = theme
      }

      setResolvedTheme(currentResolved)

      // Sync attribute on document.documentElement
      document.documentElement.setAttribute('data-theme', currentResolved)

      // Sync class on body
      const body = document.body
      if (currentResolved === 'dark') {
        body.classList.add('theme-purple-dream')
      } else {
        body.classList.remove('theme-purple-dream')
      }
    }

    applyTheme()

    // Listen to changes in OS preferences
    const handleOSThemeChange = () => {
      if (theme === 'system') {
        applyTheme()
      }
    }

    mediaQuery.addEventListener('change', handleOSThemeChange)

    // Persist globally
    localStorage.setItem('smartonboard-theme', theme)
    
    // Persist in user profile preferences
    if (user) {
      localStorage.setItem(`smartonboard-theme-${user.id}`, theme)
    }

    return () => {
      mediaQuery.removeEventListener('change', handleOSThemeChange)
    }
  }, [theme, user])

  const toggleTheme = () => {
    setThemeState((prev) => {
      if (prev === 'light') return 'dark'
      if (prev === 'dark') return 'system'
      return 'light'
    })
  }

  const setTheme = (newTheme: Theme) => {
    setThemeState(newTheme)
  }

  return (
    <ThemeContext.Provider value={{ theme, resolvedTheme, toggleTheme, setTheme }}>
      {children}
    </ThemeContext.Provider>
  )
}

export function useTheme() {
  const ctx = useContext(ThemeContext)
  if (!ctx) throw new Error('useTheme must be used within ThemeProvider')
  return ctx
}
