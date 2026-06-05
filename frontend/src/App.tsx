import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import { ThemeProvider } from './context/ThemeContext'
import ProtectedRoute from './components/ProtectedRoute'
import Landing from './pages/Landing'
import Login from './pages/Login'
import Register from './pages/Register'
import Dashboard from './pages/Dashboard'
import Results from './pages/Results'
import CandidatePortal from './pages/CandidatePortal'
import CandidateDirectory from './pages/CandidateDirectory'
import PipelineBoard from './pages/PipelineBoard'
import EmployeeDirectory from './pages/EmployeeDirectory'
import AnalyticsDashboard from './pages/AnalyticsDashboard'
import CandidateDashboard from './pages/CandidateDashboard'
import ResumeLibrary from './pages/ResumeLibrary'
import CandidateJobFeed from './pages/CandidateJobFeed'
import CandidateApplications from './pages/CandidateApplications'
import CandidateInterviews from './pages/CandidateInterviews'
import CandidateProfilePage from './pages/CandidateProfilePage'

function App() {
  return (
    <AuthProvider>
      <ThemeProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<Landing />} />
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            
            {/* RLS-Protected Recruiter Command Center Router */}
            <Route
              path="/dashboard"
              element={
                <ProtectedRoute allowedRoles={['owner', 'recruiter']}>
                  <Dashboard />
                </ProtectedRoute>
              }
            />
            <Route
              path="/candidates"
              element={
                <ProtectedRoute allowedRoles={['owner', 'recruiter']}>
                  <CandidateDirectory />
                </ProtectedRoute>
              }
            />
            <Route
              path="/pipeline"
              element={
                <ProtectedRoute allowedRoles={['owner', 'recruiter']}>
                  <PipelineBoard />
                </ProtectedRoute>
              }
            />
            <Route
              path="/employees"
              element={
                <ProtectedRoute allowedRoles={['owner', 'recruiter']}>
                  <EmployeeDirectory />
                </ProtectedRoute>
              }
            />
            <Route
              path="/analytics"
              element={
                <ProtectedRoute allowedRoles={['owner', 'recruiter']}>
                  <AnalyticsDashboard />
                </ProtectedRoute>
              }
            />

            {/* Candidate Workspace Routes */}
            <Route
              path="/candidate/dashboard"
              element={
                <ProtectedRoute allowedRoles={['candidate']}>
                  <CandidateDashboard />
                </ProtectedRoute>
              }
            />
            <Route
              path="/candidate/resumes"
              element={
                <ProtectedRoute allowedRoles={['candidate']}>
                  <ResumeLibrary />
                </ProtectedRoute>
              }
            />
            <Route
              path="/candidate/jobs"
              element={
                <ProtectedRoute allowedRoles={['candidate']}>
                  <CandidateJobFeed />
                </ProtectedRoute>
              }
            />
            <Route
              path="/candidate/applications"
              element={
                <ProtectedRoute allowedRoles={['candidate']}>
                  <CandidateApplications />
                </ProtectedRoute>
              }
            />
            <Route
              path="/candidate/interviews"
              element={
                <ProtectedRoute allowedRoles={['candidate']}>
                  <CandidateInterviews />
                </ProtectedRoute>
              }
            />
            <Route
              path="/candidate/profile"
              element={
                <ProtectedRoute allowedRoles={['candidate']}>
                  <CandidateProfilePage />
                </ProtectedRoute>
              }
            />

            <Route path="/results" element={<Results />} />
            <Route path="/candidate" element={<CandidatePortal />} />
          </Routes>
        </BrowserRouter>
      </ThemeProvider>
    </AuthProvider>
  )
}

export default App


