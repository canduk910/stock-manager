/**
 * Admin 관리 페이지 (/admin) — AI 사용량 + 한도 설정 + 감사 로그.
 * admin only 접근.
 */
import { useEffect, useState, useCallback } from 'react'
import { fetchAiUsage, fetchAiLimits, setAiLimit, deleteAiLimit, fetchAuditLog } from '../api/admin'
import LoadingSpinner from '../components/common/LoadingSpinner'
import ErrorAlert from '../components/common/ErrorAlert'

const TABS = [
  { key: 'usage', label: '사용량 현황' },
  { key: 'limits', label: '한도 설정' },
  { key: 'audit', label: '감사 로그' },
]

function UsageTab() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [date, setDate] = useState(() => {
    const d = new Date(Date.now() + 9 * 3600_000)
    return d.toISOString().slice(0, 10)
  })

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const result = await fetchAiUsage(date)
      setData(result)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [date])

  useEffect(() => { load() }, [load])

  if (loading) return <LoadingSpinner />
  if (error) return <ErrorAlert message={error} />

  const summary = data?.summary || []

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <input
          type="date"
          value={date}
          onChange={e => setDate(e.target.value)}
          className="border border-gray-300 rounded px-3 py-1.5 text-sm"
        />
        <span className="text-sm text-gray-500">KST 기준</span>
      </div>

      <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b">
            <tr>
              <th className="px-4 py-2.5 text-left font-medium text-gray-600">사용자</th>
              <th className="px-4 py-2.5 text-right font-medium text-gray-600">오늘 사용</th>
              <th className="px-4 py-2.5 text-right font-medium text-gray-600">일일 한도</th>
              <th className="px-4 py-2.5 text-right font-medium text-gray-600">잔여</th>
            </tr>
          </thead>
          <tbody>
            {summary.length === 0 ? (
              <tr><td colSpan={4} className="px-4 py-8 text-center text-gray-400">사용 이력이 없습니다.</td></tr>
            ) : summary.map(row => (
              <tr key={row.user_id} className="border-b last:border-0 hover:bg-gray-50">
                <td className="px-4 py-2.5">{row.user_name} <span className="text-gray-400 text-xs">(#{row.user_id})</span></td>
                <td className="px-4 py-2.5 text-right font-mono">{row.count}</td>
                <td className="px-4 py-2.5 text-right font-mono">{row.limit}</td>
                <td className="px-4 py-2.5 text-right font-mono">
                  <span className={row.limit - row.count <= 0 ? 'text-red-600 font-semibold' : 'text-green-600'}>
                    {Math.max(0, row.limit - row.count)}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {data?.detail?.length > 0 && (
        <div>
          <h3 className="text-sm font-medium text-gray-700 mb-2">서비스별 상세</h3>
          <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b">
                <tr>
                  <th className="px-4 py-2 text-left font-medium text-gray-600">사용자 ID</th>
                  <th className="px-4 py-2 text-left font-medium text-gray-600">서비스</th>
                  <th className="px-4 py-2 text-right font-medium text-gray-600">횟수</th>
                </tr>
              </thead>
              <tbody>
                {data.detail.map((row, i) => (
                  <tr key={i} className="border-b last:border-0 hover:bg-gray-50">
                    <td className="px-4 py-2">#{row.user_id}</td>
                    <td className="px-4 py-2"><code className="text-xs bg-gray-100 px-1.5 py-0.5 rounded">{row.service_name}</code></td>
                    <td className="px-4 py-2 text-right font-mono">{row.count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}

function LimitsTab() {
  const [limits, setLimits] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [editId, setEditId] = useState(null)
  const [editValue, setEditValue] = useState('')
  const [newUserId, setNewUserId] = useState('')
  const [newLimit, setNewLimit] = useState('50')

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const result = await fetchAiLimits()
      setLimits(result.limits || [])
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const handleSave = async (userId, dailyLimit) => {
    try {
      await setAiLimit(userId, parseInt(dailyLimit))
      setEditId(null)
      load()
    } catch (e) {
      setError(e.message)
    }
  }

  const handleDelete = async (userId) => {
    try {
      await deleteAiLimit(userId)
      load()
    } catch (e) {
      setError(e.message)
    }
  }

  const handleAdd = async () => {
    const uid = newUserId === '' ? null : parseInt(newUserId)
    await handleSave(uid, newLimit)
    setNewUserId('')
    setNewLimit('50')
  }

  if (loading) return <LoadingSpinner />
  if (error) return <ErrorAlert message={error} />

  return (
    <div className="space-y-4">
      <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b">
            <tr>
              <th className="px-4 py-2.5 text-left font-medium text-gray-600">대상</th>
              <th className="px-4 py-2.5 text-right font-medium text-gray-600">일일 한도</th>
              <th className="px-4 py-2.5 text-right font-medium text-gray-600">수정일</th>
              <th className="px-4 py-2.5 text-center font-medium text-gray-600">작업</th>
            </tr>
          </thead>
          <tbody>
            {limits.map(row => (
              <tr key={row.id} className="border-b last:border-0 hover:bg-gray-50">
                <td className="px-4 py-2.5">
                  {row.user_name}
                  {row.user_id !== null && <span className="text-gray-400 text-xs ml-1">(#{row.user_id})</span>}
                </td>
                <td className="px-4 py-2.5 text-right">
                  {editId === row.id ? (
                    <input
                      type="number"
                      value={editValue}
                      onChange={e => setEditValue(e.target.value)}
                      className="w-20 border rounded px-2 py-1 text-right text-sm"
                      min={0}
                    />
                  ) : (
                    <span className="font-mono">{row.daily_limit}</span>
                  )}
                </td>
                <td className="px-4 py-2.5 text-right text-xs text-gray-400">
                  {row.updated_at?.slice(0, 16)}
                </td>
                <td className="px-4 py-2.5 text-center space-x-2">
                  {editId === row.id ? (
                    <>
                      <button onClick={() => handleSave(row.user_id, editValue)} className="text-blue-600 hover:text-blue-800 text-xs font-medium">저장</button>
                      <button onClick={() => setEditId(null)} className="text-gray-500 hover:text-gray-700 text-xs">취소</button>
                    </>
                  ) : (
                    <>
                      <button onClick={() => { setEditId(row.id); setEditValue(String(row.daily_limit)) }} className="text-blue-600 hover:text-blue-800 text-xs font-medium">수정</button>
                      {row.user_id !== null && (
                        <button onClick={() => handleDelete(row.user_id)} className="text-red-600 hover:text-red-800 text-xs font-medium">삭제</button>
                      )}
                    </>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
        <h3 className="text-sm font-medium text-gray-700 mb-3">한도 추가</h3>
        <div className="flex items-end gap-3">
          <div>
            <label className="block text-xs text-gray-500 mb-1">User ID (비워두면 기본 한도)</label>
            <input
              type="number"
              value={newUserId}
              onChange={e => setNewUserId(e.target.value)}
              placeholder="비워두면 기본"
              className="border border-gray-300 rounded px-3 py-1.5 text-sm w-40"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">일일 한도</label>
            <input
              type="number"
              value={newLimit}
              onChange={e => setNewLimit(e.target.value)}
              className="border border-gray-300 rounded px-3 py-1.5 text-sm w-24"
              min={0}
            />
          </div>
          <button
            onClick={handleAdd}
            className="bg-blue-600 text-white px-4 py-1.5 rounded text-sm font-medium hover:bg-blue-700"
          >
            추가
          </button>
        </div>
      </div>
    </div>
  )
}

const ACTION_LABELS = {
  set_ai_limit: '한도 설정',
  delete_ai_limit: '한도 삭제',
}

function AuditTab() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetchAuditLog(200)
      .then(setData)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <LoadingSpinner />
  if (error) return <ErrorAlert message={error} />

  const items = data?.items || []

  return (
    <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
      <table className="w-full text-sm">
        <thead className="bg-gray-50 border-b">
          <tr>
            <th className="px-4 py-2.5 text-left font-medium text-gray-600">일시</th>
            <th className="px-4 py-2.5 text-left font-medium text-gray-600">관리자</th>
            <th className="px-4 py-2.5 text-left font-medium text-gray-600">작업</th>
            <th className="px-4 py-2.5 text-left font-medium text-gray-600">대상</th>
            <th className="px-4 py-2.5 text-left font-medium text-gray-600">변경 내용</th>
          </tr>
        </thead>
        <tbody>
          {items.length === 0 ? (
            <tr><td colSpan={5} className="px-4 py-8 text-center text-gray-400">감사 로그가 없습니다.</td></tr>
          ) : items.map(row => (
            <tr key={row.id} className="border-b last:border-0 hover:bg-gray-50">
              <td className="px-4 py-2.5 text-xs text-gray-500 whitespace-nowrap">{row.created_at?.slice(0, 16)}</td>
              <td className="px-4 py-2.5">{row.actor_name}</td>
              <td className="px-4 py-2.5">
                <span className="bg-blue-100 text-blue-800 text-xs px-2 py-0.5 rounded">
                  {ACTION_LABELS[row.action] || row.action}
                </span>
              </td>
              <td className="px-4 py-2.5 text-xs">
                {row.target_type}
                {row.target_id && <span className="text-gray-400 ml-1">({row.target_id})</span>}
              </td>
              <td className="px-4 py-2.5 text-xs">
                {row.old_value && (
                  <span className="text-red-600 line-through mr-2">{JSON.stringify(row.old_value)}</span>
                )}
                {row.new_value && (
                  <span className="text-green-600">{JSON.stringify(row.new_value)}</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default function AdminPage() {
  const [tab, setTab] = useState('usage')

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">AI 관리</h1>

      <div className="flex gap-1 border-b border-gray-200">
        {TABS.map(t => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              tab === t.key
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'usage' && <UsageTab />}
      {tab === 'limits' && <LimitsTab />}
      {tab === 'audit' && <AuditTab />}
    </div>
  )
}
