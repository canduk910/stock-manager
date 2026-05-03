import { useState } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './hooks/useAuth'
import Header from './components/layout/Header'
import ProtectedRoute from './components/common/ProtectedRoute'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import DashboardPage from './pages/DashboardPage'
import ScreenerPage from './pages/ScreenerPage'
import EarningsPage from './pages/EarningsPage'
import BalancePage from './pages/BalancePage'
import WatchlistPage from './pages/WatchlistPage'
import DetailPage from './pages/DetailPage'
import OrderPage from './pages/OrderPage'
import MarketBoardPage from './pages/MarketBoardPage'
import MacroPage from './pages/MacroPage'
import PortfolioPage from './pages/PortfolioPage'
import ReportPage from './pages/ReportPage'
import BacktestPage from './pages/BacktestPage'
import TaxPage from './pages/TaxPage'
import AdminPage from './pages/AdminPage'
import AdminUsersPage from './pages/AdminUsersPage'
import AdminPageStatsPage from './pages/AdminPageStatsPage'
import SettingsKisPage from './pages/SettingsKisPage'
import ToastNotification from './components/common/ToastNotification'
import { useNotification } from './hooks/useNotification'

export const WIDTH_OPTIONS = [
  { key: 'normal', label: '표준', maxCls: 'max-w-7xl mx-auto' },
  { key: 'wide',   label: '넓게', maxCls: 'max-w-screen-2xl mx-auto' },
  { key: 'full',   label: '전체', maxCls: '' },
]

export default function App() {
  const { user } = useAuth()
  const [widthKey, setWidthKey] = useState(
    () => localStorage.getItem('layout-width') || 'normal'
  )
  const { toasts, notify, removeToast } = useNotification()

  const handleWidth = (key) => {
    setWidthKey(key)
    localStorage.setItem('layout-width', key)
  }

  const maxCls = WIDTH_OPTIONS.find((o) => o.key === widthKey)?.maxCls ?? 'max-w-7xl mx-auto'

  // 로그인/회원가입 페이지는 Header 없이 렌더링
  return (
    <div className="min-h-screen bg-gray-50">
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="*" element={
          <>
            {user && <Header widthKey={widthKey} onWidthChange={handleWidth} maxCls={maxCls} />}
            <main className={`px-4 py-6 ${maxCls}`}>
              <Routes>
                <Route path="/" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
                <Route path="/screener" element={<ProtectedRoute><ScreenerPage /></ProtectedRoute>} />
                <Route path="/earnings" element={<ProtectedRoute><EarningsPage /></ProtectedRoute>} />
                <Route path="/watchlist" element={<ProtectedRoute><WatchlistPage /></ProtectedRoute>} />
                <Route path="/detail/:symbol" element={<ProtectedRoute><DetailPage /></ProtectedRoute>} />
                <Route path="/market-board" element={<ProtectedRoute><MarketBoardPage /></ProtectedRoute>} />
                <Route path="/macro" element={<ProtectedRoute><MacroPage /></ProtectedRoute>} />
                <Route path="/reports" element={<ProtectedRoute><ReportPage /></ProtectedRoute>} />
                <Route path="/backtest" element={<ProtectedRoute><BacktestPage /></ProtectedRoute>} />
                {/* User KIS settings (Phase 4 D.4) */}
                <Route path="/settings/kis" element={<ProtectedRoute><SettingsKisPage /></ProtectedRoute>} />

                {/* Asset management — KIS 자격증명 필수 (Phase 4 D.5) */}
                <Route path="/balance" element={<ProtectedRoute requireKis><BalancePage notify={notify} /></ProtectedRoute>} />
                <Route path="/order" element={<ProtectedRoute requireKis><OrderPage notify={notify} /></ProtectedRoute>} />
                <Route path="/portfolio" element={<ProtectedRoute requireKis><PortfolioPage notify={notify} /></ProtectedRoute>} />
                <Route path="/tax" element={<ProtectedRoute requireKis><TaxPage /></ProtectedRoute>} />

                {/* Admin-only routes (Phase 4 단계 4-5) */}
                <Route path="/admin" element={<Navigate to="/admin/ai" replace />} />
                <Route path="/admin/ai" element={<ProtectedRoute adminOnly><AdminPage /></ProtectedRoute>} />
                <Route path="/admin/users" element={<ProtectedRoute adminOnly><AdminUsersPage /></ProtectedRoute>} />
                <Route path="/admin/page-stats" element={<ProtectedRoute adminOnly><AdminPageStatsPage /></ProtectedRoute>} />
              </Routes>
            </main>
            <footer className="border-t border-gray-200 bg-gray-50 py-4 mt-8">
              <p className="text-center text-xs text-gray-400 leading-relaxed px-4">
                AI가 생성한 자료로, 투자 참고용으로만 제공됩니다.
                정보의 정확성이나 완전성을 보장하지 않으며, 투자 결과에 대한 법적 책임은 이용자 본인에게 있습니다.
              </p>
            </footer>
            <ToastNotification toasts={toasts} removeToast={removeToast} />
          </>
        } />
      </Routes>
    </div>
  )
}
