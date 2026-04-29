import { useState } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'
import ChangePasswordModal from '../common/ChangePasswordModal'

// 그룹별 구분: 종목 정보 | 자산 관리 (admin only)
const NAV_GROUPS = [
  // 그룹 1: 종목 정보 (all users)
  [
    { to: '/market-board', label: '시세판' },
    { to: '/watchlist', label: '관심종목' },
    {
      label: '분석',
      children: [
        { to: '/macro', label: '매크로' },
        { to: '/screener', label: '스크리너' },
        { to: '/earnings', label: '공시' },
        { to: '/reports', label: '보고서' },
        { to: '/backtest', label: '백테스트' },
      ],
    },
  ],
  // 그룹 2: 자산 관리 (admin only)
  [
    { to: '/portfolio', label: '포트폴리오' },
    {
      label: '매매',
      children: [
        { to: '/order', label: '주문' },
        { to: '/balance', label: '잔고' },
        { to: '/tax', label: '양도세' },
      ],
    },
    { to: '/admin', label: 'AI관리' },
  ],
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
        onClick={() => setOpen(v => !v)}
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

function UserMenu() {
  const { user, logout, isAdmin } = useAuth()
  const [open, setOpen] = useState(false)
  const [showPwModal, setShowPwModal] = useState(false)

  if (!user) return null

  return (
    <>
      <div
        className="relative"
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => setOpen(false)}
      >
        <button className="flex items-center gap-2 px-3 py-1.5 rounded text-sm font-medium text-gray-300 hover:bg-gray-700 hover:text-white transition-colors">
          {isAdmin && (
            <span className="px-1.5 py-0.5 bg-amber-500 text-white text-[10px] font-bold rounded">ADMIN</span>
          )}
          <span>{user.name}</span>
          <svg className="w-3 h-3 opacity-60" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </button>

        {open && (
          <div className="absolute top-full right-0 pt-1 z-50">
            <div className="bg-gray-800 rounded-lg shadow-xl border border-gray-700 py-1 min-w-[140px]">
              <button
                onClick={() => { setOpen(false); setShowPwModal(true) }}
                className="block w-full text-left px-4 py-2 text-sm text-gray-300 hover:bg-gray-700 hover:text-white transition-colors"
              >
                Change Password
              </button>
              <button
                onClick={() => { setOpen(false); logout() }}
                className="block w-full text-left px-4 py-2 text-sm text-red-400 hover:bg-gray-700 hover:text-red-300 transition-colors"
              >
                Logout
              </button>
            </div>
          </div>
        )}
      </div>
      {showPwModal && <ChangePasswordModal onClose={() => setShowPwModal(false)} />}
    </>
  )
}

export default function Header({ widthKey, onWidthChange, maxCls }) {
  const { isAdmin } = useAuth()
  const [mobileOpen, setMobileOpen] = useState(false)
  const location = useLocation()

  // admin이 아닌 경우 자산 관리 그룹(NAV_GROUPS[1]) 숨김
  const visibleGroups = isAdmin ? NAV_GROUPS : [NAV_GROUPS[0]]

  // 페이지 이동 시 모바일 메뉴 닫기
  const closeMobile = () => setMobileOpen(false)

  return (
    <header className="bg-gray-900 text-white shadow-lg">
      <div className={`${maxCls} px-4 py-3 flex items-center gap-4 md:gap-8`}>
        <NavLink to="/" className="font-bold text-lg tracking-tight hover:text-blue-400 transition-colors">
          DK STOCK
        </NavLink>

        {/* 햄버거 버튼 (모바일) */}
        <button
          className="md:hidden ml-auto p-2 -mr-2 text-gray-300 hover:text-white"
          onClick={() => setMobileOpen(v => !v)}
          aria-label="메뉴"
        >
          <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            {mobileOpen
              ? <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              : <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            }
          </svg>
        </button>

        {/* 데스크톱 네비게이션 */}
        <div className="hidden md:contents">
          <div className="w-px h-5 bg-gray-600" />
          <nav className="flex items-center gap-1">
            {visibleGroups.map((group, gi) => (
              <div key={gi} className="flex items-center gap-1">
                {gi > 0 && (
                  <div className="w-px h-5 bg-gray-600 mx-2" />
                )}
                {group.map((item) =>
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
              </div>
            ))}
          </nav>
          <div className="w-px h-5 bg-gray-600" />

          {/* 너비 선택 */}
          <div className="ml-auto flex items-center gap-4">
            <div className="flex rounded-md border border-gray-600 overflow-hidden text-xs font-medium">
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
            <UserMenu />
          </div>
        </div>

        {/* 모바일: UserMenu만 우측에 표시 */}
        <div className="md:hidden">
          <UserMenu />
        </div>
      </div>

      {/* 모바일 메뉴 패널 */}
      {mobileOpen && (
        <nav className="md:hidden border-t border-gray-700 px-4 py-3 space-y-1">
          {visibleGroups.map((group, gi) => (
            <div key={gi}>
              {gi > 0 && <div className="border-t border-gray-700 my-2" />}
              {group.map((item) =>
                item.children ? (
                  <div key={item.label} className="space-y-1">
                    <span className="block px-3 py-1 text-xs font-medium text-gray-500 uppercase">{item.label}</span>
                    {item.children.map(child => (
                      <NavLink
                        key={child.to}
                        to={child.to}
                        onClick={closeMobile}
                        className={({ isActive }) =>
                          `block px-3 py-2.5 rounded text-sm font-medium transition-colors ${
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
                ) : (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    onClick={closeMobile}
                    className={({ isActive }) =>
                      `block px-3 py-2.5 rounded text-sm font-medium transition-colors ${
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
            </div>
          ))}
        </nav>
      )}
    </header>
  )
}
