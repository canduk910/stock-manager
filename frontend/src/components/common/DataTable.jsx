/**
 * 범용 데이터 테이블 (컬럼 클릭 정렬 지원).
 *
 * columns: Array<{ key, label, align?, render? }>
 * data: Array<object>
 */
import { useState, useMemo } from 'react'

function SortIcon({ active, dir }) {
  if (!active) return <span className="ml-1 text-gray-300 text-xs">⇅</span>
  return <span className={`ml-1 text-xs ${active ? 'text-blue-500' : 'text-gray-300'}`}>{dir === 'asc' ? '▲' : '▼'}</span>
}

export default function DataTable({ columns, data, rowKey, renderContext = {} }) {
  const [sortKey, setSortKey] = useState(null)
  const [sortDir, setSortDir] = useState('asc')

  const handleSort = (key) => {
    if (sortKey === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortKey(key)
      setSortDir('asc')
    }
  }

  const sortedData = useMemo(() => {
    if (!sortKey || !data) return data
    return [...data].sort((a, b) => {
      const va = a[sortKey]
      const vb = b[sortKey]
      const na = Number(va)
      const nb = Number(vb)
      const isNum = va !== null && vb !== null && va !== '' && vb !== '' && !isNaN(na) && !isNaN(nb)
      const cmp = isNum ? na - nb : String(va ?? '').localeCompare(String(vb ?? ''), 'ko')
      return sortDir === 'asc' ? cmp : -cmp
    })
  }, [data, sortKey, sortDir])

  if (!data || data.length === 0) return null

  return (
    <div className="overflow-x-auto rounded-lg border border-gray-200">
      <table className="min-w-full text-sm">
        <thead className="bg-gray-50 border-b border-gray-200">
          <tr>
            {columns.map((col) => (
              <th
                key={col.key}
                onClick={() => col.sortable !== false && handleSort(col.key)}
                className={`px-4 py-2.5 font-semibold text-gray-600 whitespace-nowrap select-none transition-colors ${
                  col.sortable !== false ? 'cursor-pointer hover:bg-gray-100' : 'cursor-default'
                } ${
                  col.align === 'right'
                    ? 'text-right'
                    : col.align === 'center'
                    ? 'text-center'
                    : 'text-left'
                }`}
              >
                {col.label}
                {col.sortable !== false && <SortIcon active={sortKey === col.key} dir={sortDir} />}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sortedData.map((row, i) => (
            <tr
              key={rowKey ? row[rowKey] : i}
              className="border-b border-gray-100 hover:bg-gray-50 transition-colors"
            >
              {columns.map((col) => (
                <td
                  key={col.key}
                  className={`px-4 py-2.5 text-gray-700 whitespace-nowrap ${
                    col.align === 'right'
                      ? 'text-right'
                      : col.align === 'center'
                      ? 'text-center'
                      : 'text-left'
                  }`}
                >
                  {col.render ? col.render(row[col.key], row, renderContext) : (row[col.key] ?? '-')}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
