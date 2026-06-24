import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

interface ProtectedRouteProps {
  children: React.ReactNode
  allowedRoles?: string[]
}

export default function ProtectedRoute({ children, allowedRoles }: ProtectedRouteProps) {
  const { user, loading } = useAuth()
  const location = useLocation()

  if (loading) {
    return (
      <div className="container" style={{ padding: 'var(--space-16) 0', textAlign: 'center' }}>
        <div className="spinner spinner--lg" style={{ margin: '0 auto' }} />
      </div>
    )
  }

  if (!user) {
    const isCandidatePath = location.pathname.startsWith('/candidate');
    const redirectLoginPath = isCandidatePath ? '/candidate/login' : '/recruiter/login';
    return <Navigate to={redirectLoginPath} replace state={{ from: location.pathname }} />
  }

  // Recruiter Setup Company & Email Verification Guard
  if (user.role !== 'candidate') {
    if (!user.company_id) {
      if (location.pathname !== '/recruiter/setup-company') {
        return <Navigate to="/recruiter/setup-company" replace />
      }
    } else {
      if (!user.email_verified && location.pathname !== '/recruiter/verify-email') {
        return <Navigate to="/recruiter/verify-email" replace />
      }
      if (user.email_verified && (location.pathname === '/recruiter/verify-email' || location.pathname === '/recruiter/setup-company')) {
        return <Navigate to="/recruiter/dashboard" replace />
      }
    }
  }

  if (allowedRoles && !allowedRoles.includes(user.role)) {
    if (user.role === 'candidate') {
      return <Navigate to="/candidate/dashboard" replace />
    } else {
      return <Navigate to="/recruiter/dashboard" replace />
    }
  }

  // Verification Guard Check
  if (user.role === 'candidate') {
    if (!user.email_verified || !user.phone_verified) {
      localStorage.setItem('smartonboard_redirect_target', location.pathname)
      return <Navigate to="/candidate/verify" replace />
    }
  }

  // Onboarding Guard Check
  if (user.role === 'candidate') {
    const onboarded = localStorage.getItem(`smartonboard_onboarded_candidate_${user.email}`) === 'true'
    if (!onboarded && location.pathname !== '/candidate/dashboard') {
      return <Navigate to="/candidate/dashboard" replace />
    }
  } else {
    if (user.email_verified) {
      const onboarded = localStorage.getItem(`smartonboard_onboarded_recruiter_${user.email}`) === 'true'
      if (!onboarded && location.pathname !== '/recruiter/dashboard') {
        return <Navigate to="/recruiter/dashboard" replace />
      }
    }
  }

  return children
}
