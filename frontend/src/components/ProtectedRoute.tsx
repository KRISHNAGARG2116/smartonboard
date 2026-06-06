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

  if (allowedRoles && !allowedRoles.includes(user.role)) {
    if (user.role === 'candidate') {
      return <Navigate to="/candidate/dashboard" replace />
    } else {
      return <Navigate to="/recruiter/dashboard" replace />
    }
  }

  return children
}
