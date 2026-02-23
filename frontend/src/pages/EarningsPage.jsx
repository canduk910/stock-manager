import { useState, useEffect } from 'react'
import { useEarnings } from '../hooks/useEarnings'
import FilingsTable from '../components/earnings/FilingsTable'
import LoadingSpinner from '../components/common/LoadingSpinner'
import ErrorAlert from '../components/common/ErrorAlert'
import EmptyState from '../components/common/EmptyState'

function todayStr() {
  return new Date().toISOString().slice(0, 10)
}

export default function EarningsPage() {
  const [date, setDate] = useState(todayStr())
  const { data, loading, error, load } = useEarnings()

  useEffect(() => {
    load(date.replace(/-/g, ''))
  }, []) // 첫 마운트 시 오늘 날짜로 조회

  const handleSearch = () => {
    load(date.replace(/-/g, ''))
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">공시 조회</h1>

      <div className="bg-white rounded-xl border border-gray-200 p-4 flex items-end gap-3">
        <label className="flex flex-col gap-1">
          <span className="text-xs font-medium text-gray-500">조회 날짜</span>
          <input
            type="date"
            value={date}
            onChange={(e) => setDate(e.target.value)}
            className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
          />
        </label>
        <button
          onClick={handleSearch}
          disabled={loading}
          className="px-5 py-1.5 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-semibold rounded-lg text-sm transition-colors"
        >
          {loading ? '조회 중...' : '조회'}
        </button>
      </div>

      {loading && <LoadingSpinner />}
      <ErrorAlert message={error} />

      {data && !loading && (
        <>
          <p className="text-sm text-gray-500">
            <span className="font-semibold text-gray-800">{data.total}건</span>의 정기보고서 제출
            {data.date && ` (${data.date.slice(0, 4)}-${data.date.slice(4, 6)}-${data.date.slice(6)})`}
          </p>
          {data.filings.length === 0 ? (
            <EmptyState message="해당 날짜에 제출된 정기보고서가 없습니다." />
          ) : (
            <FilingsTable filings={data.filings} />
          )}
        </>
      )}
    </div>
  )
}
