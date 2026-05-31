import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from '@/hooks/useAuth'
import { Spinner } from '@/components/ui/Spinner'
import Layout from '@/components/Layout'
import Login from '@/pages/Login'
import Overview from '@/pages/Overview'
import Sources from '@/pages/Sources'
import Destinations from '@/pages/Destinations'
import RoutesPage from '@/pages/Routes'
import Deliveries from '@/pages/Deliveries'
import AuditLog from '@/pages/AuditLog'

function RequireAuth({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth()
  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#091a0d] flex items-center justify-center">
        <Spinner size={28} />
      </div>
    )
  }
  if (!isAuthenticated) return <Navigate to="/login" replace />
  return <>{children}</>
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/" element={<RequireAuth><Layout /></RequireAuth>}>
          <Route index element={<Overview />} />
          <Route path="sources"      element={<Sources />} />
          <Route path="destinations" element={<Destinations />} />
          <Route path="routes"       element={<RoutesPage />} />
          <Route path="deliveries"   element={<Deliveries />} />
          <Route path="audit-log"    element={<AuditLog />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
