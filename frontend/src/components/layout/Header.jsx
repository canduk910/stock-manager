import { NavLink } from 'react-router-dom'

const NAV_ITEMS = [
  { to: '/', label: '대시보드' },
  { to: '/screener', label: '종목 스크리너' },
  { to: '/earnings', label: '공시 조회' },
  { to: '/balance', label: '잔고 조회' },
  { to: '/watchlist', label: '관심종목' },
  { to: '/order', label: '주문' },
]

const WIDTH_OPTIONS = [
  { key: 'normal', label: '표준' },
  { key: 'wide',   label: '넓게' },
  { key: 'full',   label: '전체' },
]

export default function Header({ widthKey, onWidthChange, maxCls }) {
  return (
    <header className="bg-gray-900 text-white shadow-lg">
      <div className={`${maxCls} px-4 py-3 flex items-center gap-8`}>
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

        {/* 너비 선택 */}
        <div className="ml-auto flex rounded-md border border-gray-600 overflow-hidden text-xs font-medium">
          {WIDTH_OPTIONS.map((opt) => (
            <button
              key={opt.key}
              onClick={() => onWidthChange(opt.key)}
              className={`px-3 py-1.5 transition-colors ${
                widthKey === opt.key
                  ? 'bg-gray-100 text-gray-900'
                  : 'text-gray-400 hover:bg-gray-700 hover:text-white'
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>
    </header>
  )
}