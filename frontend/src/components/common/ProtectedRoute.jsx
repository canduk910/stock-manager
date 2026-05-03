import { Navigate } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'
import KisRequiredNotice from '../KisRequiredNotice'

export default function ProtectedRoute({ children, adminOnly = false, requireKis = false }) {
  const { user, loading, isAdmin, hasKis } = useAuth()

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
      </div>
    )
  }

  if (!user) return <Navigate to="/login" replace />
  if (adminOnly && !isAdmin) return <Navigate to="/" replace />
  if (requireKis && !hasKis) return <KisRequiredNotice />

  return children
}
