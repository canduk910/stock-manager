/**
 * 사용자 검색 콤보박스 — AI관리 LimitsTab의 user_id 입력 교체용.
 *
 * Phase 4 단계 4. 입력 시 debounce 검색 → 드롭다운 → 클릭 시 user_id 자동 선택.
 */
import { useEffect, useRef, useState } from 'react'
import { fetchUsers } from '../../api/admin'

export default function UserSearchCombo({ value, onChange, placeholder = '사용자 검색 (비우면 기본 한도)' }) {
  const [query, setQuery] = useState('')
  const [items, setItems] = useState([])
  const [open, setOpen] = useState(false)
  const [selectedLabel, setSelectedLabel] = useState('')
  const timer = useRef(null)

  useEffect(() => {
    if (!query) {
      setItems([])
      return
    }
    if (timer.current) clearTimeout(timer.current)
    timer.current = setTimeout(async () => {
      try {
        const result = await fetchUsers({ q: query, limit: 10 })
        setItems(result.items || [])
        setOpen(true)
      } catch {
        setItems([])
      }
    }, 250)
    return () => { if (timer.current) clearTimeout(timer.current) }
  }, [query])

  const handlePick = (user) => {
    onChange(String(user.id))
    setSelectedLabel(`${user.name} (#${user.id})`)
    setQuery('')
    setOpen(false)
  }

  const handleClear = () => {
    onChange('')
    setSelectedLabel('')
    setQuery('')
  }

  return (
    <div className="relative w-72">
      {value && selectedLabel ? (
        <div className="flex items-center gap-2 border border-gray-300 rounded px-3 py-1.5 text-sm bg-gray-50">
          <span className="font-medium">{selectedLabel}</span>
          <button type="button" onClick={handleClear} className="ml-auto text-gray-400 hover:text-red-600">×</button>
        </div>
      ) : (
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => query && setOpen(true)}
          onBlur={() => setTimeout(() => setOpen(false), 200)}
          placeholder={placeholder}
          className="border border-gray-300 rounded px-3 py-1.5 text-sm w-full"
        />
      )}
      {open && items.length > 0 && (
        <ul className="absolute z-20 mt-1 w-full bg-white border border-gray-200 rounded shadow-lg max-h-60 overflow-y-auto">
          {items.map((u) => (
            <li
              key={u.id}
              onMouseDown={(e) => e.preventDefault()}
              onClick={() => handlePick(u)}
              className="px-3 py-2 text-sm hover:bg-blue-50 cursor-pointer flex items-center justify-between"
            >
              <span>
                <span className="font-medium">{u.name}</span>{' '}
                <span className="text-gray-400 text-xs">@{u.username} #{u.id}</span>
              </span>
              {u.has_kis && <span className="text-green-600 text-xs">KIS✓</span>}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
