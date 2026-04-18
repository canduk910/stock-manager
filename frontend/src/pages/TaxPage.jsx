import { useState, useEffect, useCallback } from 'react'
import TaxDisclaimer from '../components/tax/TaxDisclaimer'
import TaxSummaryCards from '../components/tax/TaxSummaryCards'
import TaxBySymbolChart from '../components/tax/TaxBySymbolChart'
import TaxTransactionsTable from '../components/tax/TaxTransactionsTable'
import TaxCalculationDetail from '../components/tax/TaxCalculationDetail'
import { useTaxSummary, useTaxTransactions, useTaxCalculations } from '../hooks/useTax'
import LoadingSpinner from '../components/common/LoadingSpinner'
import ErrorAlert from '../components/common/ErrorAlert'

const TABS = [
  { key: 'summary', label: '요약' },
  { key: 'transactions', label: '매매내역' },
  { key: 'detail', label: '계산 상세' },
]

const CURRENT_YEAR = new Date().getFullYear()
const YEARS = Array.from({ length: 5 }, (_, i) => CURRENT_YEAR - i)

export default function TaxPage() {
  const [tab, setTab] = useState('summary')
  const [year, setYear] = useState(CURRENT_YEAR)
  const [syncLoading, setSyncLoading] = useState(false)

  const summary = useTaxSummary()
  const transactions = useTaxTransactions()
  const calculations = useTaxCalculations()

  // 요약 로드
  useEffect(() => {
    if (tab === 'summary') summary.load(year)
  }, [year, tab])

  // 매매내역 로드
  useEffect(() => {
    if (tab === 'transactions') transactions.load(year)
  }, [year, tab])

  // 계산 상세 로드
  useEffect(() => {
    if (tab === 'detail') calculations.load(year)
  }, [year, tab])

  // 동기화
  const handleSync = useCallback(async () => {
    setSyncLoading(true)
    try {
      const result = await transactions.sync(year)
      alert(result.message || `동기화 완료: ${result.synced}건 추가`)
      transactions.load(year)
      // 요약도 갱신
      summary.load(year)
    } catch (err) {
      alert(`동기화 실패: ${err.message}`)
    } finally {
      setSyncLoading(false)
    }
  }, [year])

  // 수동 추가
  const handleAdd = useCallback(async (body) => {
    await transactions.add(body)
    transactions.load(year)
    summary.load(year)
  }, [year])

  // 삭제
  const handleDelete = useCallback(async (id) => {
    await transactions.remove(id)
    transactions.load(year)
    summary.load(year)
  }, [year])

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-900">해외주식 양도소득세</h1>

        {/* 연도 선택 */}
        <div className="flex items-center gap-3">
          <select
            value={year}
            onChange={(e) => setYear(Number(e.target.value))}
            className="px-3 py-1.5 border rounded-lg text-sm"
          >
            {YEARS.map((y) => (
              <option key={y} value={y}>{y}년</option>
            ))}
          </select>

          <span className="text-xs text-gray-400">선입선출(FIFO)</span>
        </div>
      </div>

      <TaxDisclaimer />

      {/* 탭 */}
      <div className="flex gap-1 border-b">
        {TABS.map((t) => (
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

      {/* 탭 콘텐츠 */}
      {tab === 'summary' && (
        <div className="space-y-4">
          {summary.loading && <LoadingSpinner />}
          {summary.error && <ErrorAlert message={summary.error} />}
          {summary.data && (
            <>
              <TaxSummaryCards summary={summary.data} />
              {summary.data.warnings?.length > 0 && (
                <div className="bg-amber-50 border border-amber-200 rounded-lg px-4 py-3 text-sm text-amber-800">
                  <span className="font-medium">경고:</span>{' '}
                  {summary.data.warnings.join(' / ')}
                </div>
              )}
              <TaxBySymbolChart bySymbol={summary.data.by_symbol} />
            </>
          )}
        </div>
      )}

      {tab === 'transactions' && (
        <div>
          {transactions.loading && <LoadingSpinner />}
          {transactions.error && <ErrorAlert message={transactions.error} />}
          <TaxTransactionsTable
            transactions={transactions.data?.transactions}
            onAdd={handleAdd}
            onDelete={handleDelete}
            onSync={handleSync}
            syncLoading={syncLoading}
            year={year}
          />
        </div>
      )}

      {tab === 'detail' && (
        <div>
          {calculations.loading && <LoadingSpinner />}
          {calculations.error && <ErrorAlert message={calculations.error} />}
          <TaxCalculationDetail calculations={calculations.data?.calculations} />
        </div>
      )}
    </div>
  )
}
