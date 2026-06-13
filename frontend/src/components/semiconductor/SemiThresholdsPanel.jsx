/**
 * 관리자 임계값 편집 패널 (모달 마지막 섹션).
 *
 * 관리자(role==='admin')만 노출. 백엔드도 require_admin으로 이중 가드.
 */

import { useState } from 'react'
import { useSemiconductorThresholds } from '../../hooks/useSemiconductor'
import { useAuth } from '../../hooks/useAuth'

function _stringifyValue(v) {
  if (v === null || v === undefined) return ''
  if (typeof v === 'string') return v
  return JSON.stringify(v)
}

function _parseValue(raw) {
  // 숫자/문자/JSON 자동 판별
  if (raw === '') return null
  const num = Number(raw)
  if (!Number.isNaN(num) && /^-?\d+(?:\.\d+)?$/.test(raw.trim())) return num
  try {
    return JSON.parse(raw)
  } catch {
    return raw  // plain string
  }
}

export default function SemiThresholdsPanel() {
  const auth = useAuth()
  const user = auth?.user
  const { data, loading, error, upsert, reload } = useSemiconductorThresholds()
  const [editValues, setEditValues] = useState({})
  const [saving, setSaving] = useState({})
  const [msg, setMsg] = useState(null)

  if (user?.role !== 'admin') {
    return (
      <div className="text-xs text-gray-500">
        ⚙ 임계값 편집은 관리자 권한이 필요합니다.
      </div>
    )
  }
  if (loading && !data) return <div className="text-gray-400 text-sm">로딩…</div>
  if (error && !data) return <div className="text-red-500 text-sm">임계값 로딩 실패</div>

  const rows = data?.thresholds || []

  const handleSave = async (row) => {
    const key = `${row.indicator_name}/${row.threshold_key}`
    const raw = editValues[key] ?? _stringifyValue(row.value)
    setSaving((s) => ({ ...s, [key]: true }))
    setMsg(null)
    try {
      await upsert(row.indicator_name, row.threshold_key, _parseValue(raw))
      setMsg({ kind: 'ok', text: `${key} 저장 완료` })
      setEditValues((v) => {
        const { [key]: _, ...rest } = v
        return rest
      })
    } catch (e) {
      setMsg({ kind: 'err', text: `${key} 저장 실패: ${e.message || e}` })
    } finally {
      setSaving((s) => ({ ...s, [key]: false }))
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <h4 className="text-sm font-semibold text-gray-700">임계값 관리 (관리자)</h4>
        <button
          type="button"
          onClick={reload}
          className="text-xs text-blue-600 hover:underline"
        >
          새로고침
        </button>
      </div>
      {msg && (
        <div
          className={`text-xs mb-2 ${
            msg.kind === 'ok' ? 'text-green-700' : 'text-red-700'
          }`}
        >
          {msg.text}
        </div>
      )}
      <div className="overflow-x-auto">
        <table className="w-full text-xs border">
          <thead className="bg-gray-50">
            <tr>
              <th className="text-left px-2 py-1">indicator</th>
              <th className="text-left px-2 py-1">key</th>
              <th className="text-left px-2 py-1">value</th>
              <th className="text-left px-2 py-1">comment</th>
              <th className="text-left px-2 py-1">updated</th>
              <th className="px-2 py-1"></th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const k = `${row.indicator_name}/${row.threshold_key}`
              const editing = editValues[k] !== undefined
              const displayValue = editing ? editValues[k] : _stringifyValue(row.value)
              return (
                <tr key={k} className="border-t">
                  <td className="px-2 py-1 font-mono text-[11px]">{row.indicator_name}</td>
                  <td className="px-2 py-1 font-mono text-[11px]">{row.threshold_key}</td>
                  <td className="px-2 py-1">
                    <input
                      type="text"
                      value={displayValue}
                      onChange={(e) =>
                        setEditValues((v) => ({ ...v, [k]: e.target.value }))
                      }
                      className="border rounded px-1 py-0.5 text-xs w-full font-mono"
                    />
                  </td>
                  <td className="px-2 py-1 text-gray-600">{row.comment || '—'}</td>
                  <td className="px-2 py-1 text-[10px] text-gray-400">
                    {row.updated_at?.slice(0, 16) || '—'}
                  </td>
                  <td className="px-2 py-1">
                    <button
                      type="button"
                      onClick={() => handleSave(row)}
                      disabled={!!saving[k]}
                      className="text-xs px-2 py-0.5 rounded bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
                    >
                      {saving[k] ? '저장 중…' : '저장'}
                    </button>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
      <div className="text-[11px] text-gray-500 mt-2">
        값은 숫자 / 문자 / JSON 자동 인식. AI IPO 공모가 수동 시드:{' '}
        <code className="bg-gray-100 px-1 rounded">ai_ipo/{`{TICKER}`}/ipo_price</code>
      </div>
    </div>
  )
}
