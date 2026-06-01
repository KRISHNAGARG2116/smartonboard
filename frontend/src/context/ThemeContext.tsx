import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { useAuth } from './AuthContext'

export type Theme = 'light' | 'dark'

interface ThemeContextValue {
  theme: Theme
  toggleTheme: () => void
  setTheme: (theme: Theme) => void
}

const ThemeContext = createContext<ThemeContextValue | null>(null)

export function ThemeProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth()
  
  const [theme, setThemeState] = useState<Theme>(() => {
    const saved = localStorage.getItem('smartonboard-theme')
    if (saved === 'light' || saved === 'dark') {
      return saved
    }
    return 'light' // Default is Light (Ocean Blue)
  })

  // Sync theme when user state changes (e.g. login)
  useEffect(() => {
    if (user) {
      const userSaved = localStorage.getItem(`smartonboard-theme-${user.id}`)
      if (userSaved === 'light' || userSaved === 'dark') {
        setThemeState(userSaved)
      }
    }
  }, [user])

  useEffect(() => {
    // Sync class on body
    const body = document.body
    if (theme === 'dark') {
      body.classList.add('theme-purple-dream')
    } else {
      body.classList.remove('theme-purple-dream')
    }
    
    // Persist globally
    localStorage.setItem('smartonboard-theme', theme)
    
    // Persist in user profile preferences
    if (user) {
      localStorage.setItem(`smartonboard-theme-${user.id}`, theme)
    }
  }, [theme, user])

  const toggleTheme = () => {
    setThemeState((prev) => (prev === 'light' ? 'dark' : 'light'))
  }

  const setTheme = (newTheme: Theme) => {
    setThemeState(newTheme)
  }

  return (
    <ThemeContext.Provider value={{ theme, toggleTheme, setTheme }}>
      {children}
    </ThemeContext.Provider>
  )
}

export function useTheme() {
  const ctx = useContext(ThemeContext)
  if (!ctx) throw new Error('useTheme must be used within ThemeProvider')
  return ctx
}

