import { useState } from 'react'
import { NavLink, useLocation } from 'react-router-dom'

const NAV_ITEMS = [
  { to: '/portfolio', label: '포트폴리오' },
  {
    label: '분석',
    children: [
      { to: '/macro', label: '매크로' },
      { to: '/screener', label: '스크리너' },
      { to: '/earnings', label: '공시' },
    ],
  },
  { to: '/watchlist', label: '관심종목' },
  {
    label: '매매',
    children: [
      { to: '/order', label: '주문' },
      { to: '/balance', label: '잔고' },
    ],
  },
  { to: '/market-board', label: '시세판' },
]

const WIDTH_OPTIONS = [
  { key: 'normal', label: '표준' },
  { key: 'wide',   label: '넓게' },
  { key: 'full',   label: '전체' },
]

function DropdownMenu({ item }) {
  const [open, setOpen] = useState(false)
  const location = useLocation()
  const isGroupActive = item.children.some(c => location.pathname.startsWith(c.to))

  return (
    <div
      className="relative"
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
    >
      <button
        className={`px-3 py-1.5 rounded text-sm font-medium transition-colors flex items-center gap-1 ${
          isGroupActive
            ? 'bg-blue-600 text-white'
            : 'text-gray-300 hover:bg-gray-700 hover:text-white'
        }`}
      >
        {item.label}
        <svg className="w-3 h-3 opacity-60" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {open && (
        <div className="absolute top-full left-0 pt-1 z-50">
          <div className="bg-gray-800 rounded-lg shadow-xl border border-gray-700 py-1 min-w-[120px]">
            {item.children.map(child => (
              <NavLink
                key={child.to}
                to={child.to}
                onClick={() => setOpen(false)}
                className={({ isActive }) =>
                  `block px-4 py-2 text-sm transition-colors ${
                    isActive
                      ? 'bg-blue-600 text-white'
                      : 'text-gray-300 hover:bg-gray-700 hover:text-white'
                  }`
                }
              >
                {child.label}
              </NavLink>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export default function Header({ widthKey, onWidthChange, maxCls }) {
  return (
    <header className="bg-gray-900 text-white shadow-lg">
      <div className={`${maxCls} px-4 py-3 flex items-center gap-8`}>
        <NavLink to="/" className="font-bold text-lg tracking-tight hover:text-blue-400 transition-colors">
          DK STOCK
        </NavLink>
        <nav className="flex gap-1">
          {NAV_ITEMS.map((item) =>
            item.children ? (
              <DropdownMenu key={item.label} item={item} />
            ) : (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `px-3 py-1.5 rounded text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-blue-600 text-white'
                      : 'text-gray-300 hover:bg-gray-700 hover:text-white'
                  }`
                }
              >
                {item.label}
              </NavLink>
            )
          )}
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
