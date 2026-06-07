import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import { ThemeProvider } from './context/ThemeContext'
import ProtectedRoute from './components/ProtectedRoute'
import Landing from './pages/Landing'

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
import CandidateDashboard from './pages/CandidateDashboard'
import ResumeLibrary from './pages/ResumeLibrary'
import CandidateJobFeed from './pages/CandidateJobFeed'
import CandidateApplications from './pages/CandidateApplications'
import CandidateInterviews from './pages/CandidateInterviews'
import CandidateProfilePage from './pages/CandidateProfilePage'
import CandidateSettings from './pages/candidate/CandidateSettings'

// Legacy / Support
import Results from './pages/Results'
import EmployeeDirectory from './pages/EmployeeDirectory'

function App() {
  return (
    <AuthProvider>
      <ThemeProvider>
        <BrowserRouter>
          <Routes>
            {/* Guest Entry Routing */}
            <Route path="/" element={<Landing />} />
            <Route path="/recruiter/login" element={<RecruiterLogin />} />
            <Route path="/recruiter/register" element={<RecruiterRegister />} />
            <Route path="/candidate/login" element={<CandidateLogin />} />
            <Route path="/candidate/register" element={<CandidateRegister />} />

            {/* Recruiter Workspace Routes (Prefixed with /recruiter/) */}
            <Route
              path="/recruiter/dashboard"
              element={
                <ProtectedRoute allowedRoles={['owner', 'recruiter']}>
                  <RecruiterDashboard />
                </ProtectedRoute>
              }
            />
            <Route
              path="/recruiter/jobs"
              element={
                <ProtectedRoute allowedRoles={['owner', 'recruiter']}>
                  <RecruiterJobs />
                </ProtectedRoute>
              }
            />
            <Route
              path="/recruiter/candidates"
              element={
                <ProtectedRoute allowedRoles={['owner', 'recruiter']}>
                  <CandidateDirectory />
                </ProtectedRoute>
              }
            />
            <Route
              path="/recruiter/pipeline"
              element={
                <ProtectedRoute allowedRoles={['owner', 'recruiter']}>
                  <PipelineBoard />
                </ProtectedRoute>
              }
            />
            <Route
              path="/recruiter/interviews"
              element={
                <ProtectedRoute allowedRoles={['owner', 'recruiter']}>
                  <RecruiterInterviews />
                </ProtectedRoute>
              }
            />
            <Route
              path="/recruiter/analytics"
              element={
                <ProtectedRoute allowedRoles={['owner', 'recruiter']}>
                  <AnalyticsDashboard />
                </ProtectedRoute>
              }
            />
            <Route
              path="/recruiter/settings"
              element={
                <ProtectedRoute allowedRoles={['owner', 'recruiter']}>
                  <RecruiterSettings />
                </ProtectedRoute>
              }
            />

            {/* Candidate Workspace Routes (Prefixed with /candidate/) */}
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
            <Route
              path="/candidate/settings"
              element={
                <ProtectedRoute allowedRoles={['candidate']}>
                  <CandidateSettings />
                </ProtectedRoute>
              }
            />

            {/* Hidden Legacy compatibilities */}
            <Route
              path="/recruiter/employees"
              element={
                <ProtectedRoute allowedRoles={['owner', 'recruiter']}>
                  <EmployeeDirectory />
                </ProtectedRoute>
              }
            />
            <Route path="/results" element={<Results />} />

            {/* Wildcard Fallbacks */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </ThemeProvider>
    </AuthProvider>
  )
}

export default App
