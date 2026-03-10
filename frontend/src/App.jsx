import { useState } from 'react'
import { Routes, Route } from 'react-router-dom'
import Header from './components/layout/Header'
import DashboardPage from './pages/DashboardPage'
import ScreenerPage from './pages/ScreenerPage'
import EarningsPage from './pages/EarningsPage'
import BalancePage from './pages/BalancePage'
import WatchlistPage from './pages/WatchlistPage'
import DetailPage from './pages/DetailPage'
import OrderPage from './pages/OrderPage'
import ToastNotification from './components/common/ToastNotification'
import { useNotification } from './hooks/useNotification'

export const WIDTH_OPTIONS = [
  { key: 'normal', label: '표준', maxCls: 'max-w-7xl mx-auto' },
  { key: 'wide',   label: '넓게', maxCls: 'max-w-screen-2xl mx-auto' },
  { key: 'full',   label: '전체', maxCls: '' },
]

export default function App() {
  const [widthKey, setWidthKey] = useState(
    () => localStorage.getItem('layout-width') || 'normal'
  )
  const { toasts, notify, removeToast } = useNotification()

  const handleWidth = (key) => {
    setWidthKey(key)
    localStorage.setItem('layout-width', key)
  }

  const maxCls = WIDTH_OPTIONS.find((o) => o.key === widthKey)?.maxCls ?? 'max-w-7xl mx-auto'

  return (
    <div className="min-h-screen bg-gray-50">
      <Header widthKey={widthKey} onWidthChange={handleWidth} maxCls={maxCls} />
      <main className={`px-4 py-6 ${maxCls}`}>
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/screener" element={<ScreenerPage />} />
          <Route path="/earnings" element={<EarningsPage />} />
          <Route path="/balance" element={<BalancePage notify={notify} />} />
          <Route path="/watchlist" element={<WatchlistPage />} />
          <Route path="/detail/:symbol" element={<DetailPage />} />
          <Route path="/order" element={<OrderPage notify={notify} />} />
        </Routes>
      </main>
      <ToastNotification toasts={toasts} removeToast={removeToast} />
    </div>
  )
}