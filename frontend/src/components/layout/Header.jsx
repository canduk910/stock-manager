import { NavLink } from 'react-router-dom'

const NAV_ITEMS = [
  { to: '/', label: '대시보드' },
  { to: '/screener', label: '종목 스크리너' },
  { to: '/earnings', label: '공시 조회' },
  { to: '/balance', label: '잔고 조회' },
  { to: '/watchlist', label: '관심종목' },
]

export default function Header() {
  return (
    <header className="bg-gray-900 text-white shadow-lg">
      <div className="max-w-7xl mx-auto px-4 py-3 flex items-center gap-8">
        <span className="font-bold text-lg tracking-tight">DK STOCK</span>
        <nav className="flex gap-1">
          {NAV_ITEMS.map(({ to, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                `px-3 py-1.5 rounded text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-300 hover:bg-gray-700 hover:text-white'
                }`
              }
            >
              {label}
            </NavLink>
          ))}
        </nav>
      </div>
    </header>
  )
}
