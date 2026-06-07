import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import { ThemeProvider } from './context/ThemeContext'
import ProtectedRoute from './components/ProtectedRoute'
import Landing from './pages/Landing'
import Login from './pages/Login'
import Register from './pages/Register'

// Split Auth Pages
import RecruiterLogin from './pages/recruiter/RecruiterLogin'
import RecruiterRegister from './pages/recruiter/RecruiterRegister'
import CandidateLogin from './pages/candidate/CandidateLogin'
import CandidateRegister from './pages/candidate/CandidateRegister'

// Recruiter Workspace Pages
import RecruiterDashboard from './pages/recruiter/RecruiterDashboard'
import CandidateDirectory from './pages/CandidateDirectory'
import PipelineBoard from './pages/PipelineBoard'
import AnalyticsDashboard from './pages/AnalyticsDashboard'
import RecruiterJobs from './pages/recruiter/RecruiterJobs'
import RecruiterInterviews from './pages/recruiter/RecruiterInterviews'
import RecruiterSettings from './pages/recruiter/RecruiterSettings'

// Candidate Workspace Pages
import CandidateDashboard from './pages/candidate/CandidateDashboard'
import ResumeLibrary from './pages/ResumeLibrary'
import CandidateJobFeed from './pages/CandidateJobFeed'
import CandidateApplications from './pages/CandidateApplications'
import CandidateInterviews from './pages/CandidateInterviews'
import CandidateProfilePage from './pages/CandidateProfilePage'
import CandidateSettings from './pages/candidate/CandidateSettings'

import { AnimatePresence } from 'framer-motion'
import { useLocation } from 'react-router-dom'
import AnimatedPage from './components/AnimatedPage'

function AppRoutes() {
  const location = useLocation()
  return (
    <AnimatePresence mode="wait">
      <Routes location={location} key={location.pathname}>
        {/* Guest Entry Routing */}
        <Route path="/" element={<AnimatedPage><Landing /></AnimatedPage>} />
        <Route path="/login" element={<AnimatedPage><Login /></AnimatedPage>} />
        <Route path="/register" element={<AnimatedPage><Register /></AnimatedPage>} />
        <Route path="/recruiter/login" element={<AnimatedPage><RecruiterLogin /></AnimatedPage>} />
        <Route path="/recruiter/register" element={<AnimatedPage><RecruiterRegister /></AnimatedPage>} />
        <Route path="/candidate/login" element={<AnimatedPage><CandidateLogin /></AnimatedPage>} />
        <Route path="/candidate/register" element={<AnimatedPage><CandidateRegister /></AnimatedPage>} />

        {/* Recruiter Workspace Routes (Prefixed with /recruiter/) */}
        <Route
          path="/recruiter/dashboard"
          element={
            <ProtectedRoute allowedRoles={['owner', 'recruiter']}>
              <AnimatedPage><RecruiterDashboard /></AnimatedPage>
            </ProtectedRoute>
          }
        />
        <Route
          path="/recruiter/jobs"
          element={
            <ProtectedRoute allowedRoles={['owner', 'recruiter']}>
              <AnimatedPage><RecruiterJobs /></AnimatedPage>
            </ProtectedRoute>
          }
        />
        <Route
          path="/recruiter/candidates"
          element={
            <ProtectedRoute allowedRoles={['owner', 'recruiter']}>
              <AnimatedPage><CandidateDirectory /></AnimatedPage>
            </ProtectedRoute>
          }
        />
        <Route
          path="/recruiter/pipeline"
          element={
            <ProtectedRoute allowedRoles={['owner', 'recruiter']}>
              <AnimatedPage><PipelineBoard /></AnimatedPage>
            </ProtectedRoute>
          }
        />
        <Route
          path="/recruiter/interviews"
          element={
            <ProtectedRoute allowedRoles={['owner', 'recruiter']}>
              <AnimatedPage><RecruiterInterviews /></AnimatedPage>
            </ProtectedRoute>
          }
        />
        <Route
          path="/recruiter/analytics"
          element={
            <ProtectedRoute allowedRoles={['owner', 'recruiter']}>
              <AnimatedPage><AnalyticsDashboard /></AnimatedPage>
            </ProtectedRoute>
          }
        />
        <Route
          path="/recruiter/settings"
          element={
            <ProtectedRoute allowedRoles={['owner', 'recruiter']}>
              <AnimatedPage><RecruiterSettings /></AnimatedPage>
            </ProtectedRoute>
          }
        />

        {/* Candidate Workspace Routes (Prefixed with /candidate/) */}
        <Route
          path="/candidate/dashboard"
          element={
            <ProtectedRoute allowedRoles={['candidate']}>
              <AnimatedPage><CandidateDashboard /></AnimatedPage>
            </ProtectedRoute>
          }
        />
        <Route
          path="/candidate/resumes"
          element={
            <ProtectedRoute allowedRoles={['candidate']}>
              <AnimatedPage><ResumeLibrary /></AnimatedPage>
            </ProtectedRoute>
          }
        />
        <Route
          path="/candidate/jobs"
          element={
            <ProtectedRoute allowedRoles={['candidate']}>
              <AnimatedPage><CandidateJobFeed /></AnimatedPage>
            </ProtectedRoute>
          }
        />
        <Route
          path="/candidate/applications"
          element={
            <ProtectedRoute allowedRoles={['candidate']}>
              <AnimatedPage><CandidateApplications /></AnimatedPage>
            </ProtectedRoute>
          }
        />
        <Route
          path="/candidate/interviews"
          element={
            <ProtectedRoute allowedRoles={['candidate']}>
              <AnimatedPage><CandidateInterviews /></AnimatedPage>
            </ProtectedRoute>
          }
        />
        <Route
          path="/candidate/profile"
          element={
            <ProtectedRoute allowedRoles={['candidate']}>
              <AnimatedPage><CandidateProfilePage /></AnimatedPage>
            </ProtectedRoute>
          }
        />
        <Route
          path="/candidate/settings"
          element={
            <ProtectedRoute allowedRoles={['candidate']}>
              <AnimatedPage><CandidateSettings /></AnimatedPage>
            </ProtectedRoute>
          }
        />

        {/* Wildcard Fallbacks */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AnimatePresence>
  )
}

function App() {
  return (
    <AuthProvider>
      <ThemeProvider>
        <BrowserRouter>
          <AppRoutes />
        </BrowserRouter>
      </ThemeProvider>
    </AuthProvider>
  )
}

export default App
