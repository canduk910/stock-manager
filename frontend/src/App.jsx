import { Routes, Route } from 'react-router-dom'
import Header from './components/layout/Header'
import DashboardPage from './pages/DashboardPage'
import ScreenerPage from './pages/ScreenerPage'
import EarningsPage from './pages/EarningsPage'
import BalancePage from './pages/BalancePage'
import WatchlistPage from './pages/WatchlistPage'
import DetailPage from './pages/DetailPage'

export default function App() {
  return (
    <div className="min-h-screen bg-gray-50">
      <Header />
      <main className="max-w-7xl mx-auto px-4 py-6">
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/screener" element={<ScreenerPage />} />
          <Route path="/earnings" element={<EarningsPage />} />
          <Route path="/balance" element={<BalancePage />} />
          <Route path="/watchlist" element={<WatchlistPage />} />
          <Route path="/detail/:symbol" element={<DetailPage />} />
        </Routes>
      </main>
    </div>
  )
}
