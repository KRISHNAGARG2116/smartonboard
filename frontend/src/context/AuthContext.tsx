import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import {
  fetchMe,
  getAuthToken,
  login as apiLogin,
  register as apiRegister,
  setAuthToken,
  type User,
  loginCandidate as apiLoginCandidate,
  registerCandidate as apiRegisterCandidate,
  fetchCandidateMe,
  loginWithGoogle as apiLoginWithGoogle,
  setupCompany as apiSetupCompany
} from '../api'

function parseJwt(token: string) {
  try {
    const base64Url = token.split('.')[1]
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/')
    const jsonPayload = decodeURIComponent(
      window.atob(base64)
        .split('')
        .map(c => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
        .join('')
    )
    return JSON.parse(jsonPayload)
  } catch {
    return null
  }
}

interface AuthContextValue {
  user: User | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  register: (data: { company_name: string; email: string; password: string; full_name: string }) => Promise<void>
  loginCandidate: (email: string, password: string) => Promise<any>
  registerCandidate: (data: { email: string; password: string; full_name: string; phone_number: string }) => Promise<any>
  loginWithGoogle: (credential: string, role: string) => Promise<any>
  setupCompany: (data: { company_name: string; company_website: string; company_domain: string; industry: string; company_size: string }) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  const loadUser = useCallback(async () => {
    const token = getAuthToken()
    if (!token) {
      setUser(null)
      setLoading(false)
      return
    }
    try {
      const decoded = parseJwt(token)
      if (decoded && decoded.role === 'candidate') {
        const me = await fetchCandidateMe()
        setUser(me)
      } else {
        const me = await fetchMe()
        setUser(me)
      }
    } catch {
      setAuthToken(null)
      setUser(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadUser()
  }, [loadUser])

  const login = useCallback(async (email: string, password: string) => {
    const res = await apiLogin({ email, password })
    setAuthToken(res.access_token || null)
    setUser(res.user)
  }, [])

  const register = useCallback(async (data: { company_name: string; email: string; password: string; full_name: string }) => {
    const res = await apiRegister(data)
    setAuthToken(res.access_token || null)
    setUser(res.user)
  }, [])

  const loginCandidate = useCallback(async (email: string, password: string) => {
    const res = await apiLoginCandidate({ email, password })
    if (res.access_token) {
      setAuthToken(res.access_token)
      setUser(res.user)
    }
    return res
  }, [])

  const registerCandidate = useCallback(async (data: { email: string; password: string; full_name: string; phone_number: string }) => {
    const res = await apiRegisterCandidate(data)
    if (res.access_token) {
      setAuthToken(res.access_token)
      setUser(res.user)
    }
    return res
  }, [])

  const loginWithGoogle = useCallback(async (credential: string, role: string) => {
    const res = await apiLoginWithGoogle({ credential, role })
    if (res.access_token) {
      setAuthToken(res.access_token)
      setUser(res.user)
    }
    return res
  }, [])

  const setupCompany = useCallback(async (data: {
    company_name: string
    company_website: string
    company_domain: string
    industry: string
    company_size: string
  }) => {
    const res = await apiSetupCompany(data)
    setAuthToken(res.access_token || null)
    setUser(res.user)
  }, [])

  const logout = useCallback(() => {
    setAuthToken(null)
    setUser(null)
  }, [])

  const value = useMemo(
    () => ({ user, loading, login, register, loginCandidate, registerCandidate, loginWithGoogle, setupCompany, logout }),
    [user, loading, login, register, loginCandidate, registerCandidate, loginWithGoogle, setupCompany, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
