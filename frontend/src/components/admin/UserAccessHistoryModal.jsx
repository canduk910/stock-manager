/**
 * UserAccessHistoryModal — 사용자별 일별 접속 이력 모달 (admin only).
 *
 * AdminUsersPage 방문수 또는 '이력' 버튼 클릭 시 오픈.
 * 7/30/90/180일 토글 + Recharts ComposedChart(PV 막대 + 고유 path 라인 보조축) + Top 5 경로.
 * ESC + 백드롭 클릭 시 닫힘.
 */
import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { fetchUserAccessHistory } from '../../api/admin'
import EmptyState from '../common/EmptyState'
import ErrorAlert from '../common/ErrorAlert'
import LoadingSpinner from '../common/LoadingSpinner'

const RANGES = [
  { key: 7, label: '7일' },
  { key: 30, label: '30일' },
  { key: 90, label: '90일' },
  { key: 180, label: '180일' },
]

function formatLastSeen(iso) {
  if (!iso) return '—'
  // "2026-05-17T19:00:00+09:00" → "2026-05-17 19:00"
  const m = iso.match(/^(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2})/)
  return m ? `${m[1]} ${m[2]}` : iso
}

function MaxBarTickFormatter(value) {
  // 0 막대도 숫자로 표시
  return value
}

export default function UserAccessHistoryModal({ user, onClose }) {
  const [days, setDays] = useState(30)
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const userId = user?.id

  const load = useCallback(
    (signal) => {
      if (!userId) return
      setLoading(true)
      setError(null)
      fetchUserAccessHistory(userId, { days })
        .then((res) => {
          if (signal?.aborted) return
          setData(res)
        })
        .catch((e) => {
          if (signal?.aborted) return
          setError(e.message)
        })
        .finally(() => {
          if (signal?.aborted) return
          setLoading(false)
        })
    },
    [userId, days],
  )

  useEffect(() => {
    const controller = new AbortController()
    load(controller.signal)
    return () => controller.abort()
  }, [load])

  // ESC 키 닫기
  useEffect(() => {
    const onKey = (e) => {
      if (e.key === 'Escape') onClose?.()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  const chartData = useMemo(() => {
    if (!data?.daily) return []
    // X축 라벨 단축: 30일 이하 MM-DD / 90일 이상 YYYY-MM
    return data.daily.map((d) => ({
      ...d,
      label: days <= 30 ? d.date.slice(5) : d.date.slice(0, 7),
    }))
  }, [data, days])

  const isEmpty = data && data.total_views === 0

  // 백드롭 클릭 닫기
  const onBackdrop = (e) => {
    if (e.target === e.currentTarget) onClose?.()
  }

  return (
    <div
      onClick={onBackdrop}
      className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4"
    >
      <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-y-auto">
        {/* 헤더 */}
        <div className="flex items-start justify-between border-b px-5 py-3.5">
          <div>
            <h2 className="text-lg font-bold text-gray-900">접속 이력</h2>
            <p className="text-xs text-gray-500 mt-0.5">
              @{user?.username} {user?.name} · 가입일 {user?.created_at?.slice(0, 10) || '—'} ·
              마지막 접속 {formatLastSeen(data?.last_seen_at)}
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-700 text-2xl leading-none p-1"
            aria-label="닫기"
          >×</button>
        </div>

        {/* 본문 */}
        <div className="px-5 py-4 space-y-4">
          {/* 상단: 누적 PV + days 토글 */}
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <span className="text-sm text-gray-500">누적 PV</span>
              <span className="ml-2 text-2xl font-bold text-gray-900 font-mono">
                {(data?.total_views ?? 0).toLocaleString()}
              </span>
            </div>
            <div className="flex gap-1">
              {RANGES.map((r) => (
                <button
                  key={r.key}
                  onClick={() => setDays(r.key)}
                  className={`px-3 py-1.5 text-sm rounded ${
                    days === r.key
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >{r.label}</button>
              ))}
            </div>
          </div>

          {error && <ErrorAlert message={error} />}
          {loading ? (
            <LoadingSpinner />
          ) : isEmpty ? (
            <EmptyState message="접속 기록 없음" />
          ) : (
            <>
              {/* 차트 */}
              <div className="border border-gray-200 rounded p-3">
                <h3 className="text-sm font-medium text-gray-700 mb-2">일별 PV + 고유 경로 수</h3>
                <ResponsiveContainer width="100%" height={260}>
                  <ComposedChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis
                      dataKey="label"
                      tick={{ fontSize: 10 }}
                      interval={days > 60 ? Math.floor(days / 12) : 'preserveEnd'}
                    />
                    <YAxis
                      yAxisId="left"
                      tick={{ fontSize: 11 }}
                      allowDecimals={false}
                      tickFormatter={MaxBarTickFormatter}
                    />
                    <YAxis
                      yAxisId="right"
                      orientation="right"
                      tick={{ fontSize: 11 }}
                      allowDecimals={false}
                    />
                    <Tooltip
                      labelFormatter={(_, payload) => payload?.[0]?.payload?.date ?? ''}
                      formatter={(value, name) => [value, name === 'views' ? 'PV' : '고유 경로 수']}
                    />
                    <Legend
                      wrapperStyle={{ fontSize: 11 }}
                      formatter={(v) => (v === 'views' ? 'PV' : '고유 경로 수')}
                    />
                    <Bar yAxisId="left" dataKey="views" fill="#2563eb" name="views" />
                    <Line
                      yAxisId="right"
                      type="monotone"
                      dataKey="unique_paths"
                      stroke="#dc2626"
                      strokeWidth={2}
                      dot={false}
                      name="unique_paths"
                    />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>

              {/* Top 경로 */}
              <div className="border border-gray-200 rounded">
                <div className="px-3 py-2 border-b bg-gray-50">
                  <h3 className="text-sm font-medium text-gray-700">
                    Top {data?.top_paths?.length ?? 0} 경로 ({days}일)
                  </h3>
                </div>
                {(data?.top_paths || []).length === 0 ? (
                  <p className="px-3 py-4 text-center text-sm text-gray-400">경로 데이터 없음</p>
                ) : (
                  <ul className="divide-y">
                    {data.top_paths.map((p) => (
                      <li key={p.path} className="flex items-center justify-between px-3 py-2 text-sm">
                        <span className="font-mono text-xs text-gray-700 truncate flex-1 pr-3">
                          {p.path}
                        </span>
                        <span className="font-mono text-gray-900">{p.views.toLocaleString()}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
