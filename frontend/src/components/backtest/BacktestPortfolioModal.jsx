/**
 * BacktestPortfolioModal — 다종목(포트폴리오) 백테스트 결과 모달.
 *
 * BacktestHistoryTable의 "보기" 버튼에서 isPortfolio=true 인 job 행을 클릭하면 열린다.
 * 단일 종목 행은 기존 onSelect 흐름(상세 패널 표시)을 유지한다.
 *
 * 표시 내용:
 *  1. 헤더: 일시 / 전략명 / 기간 / 최종 수익률·샤프·MDD
 *  2. 종목 칩 리스트 (symbols_names 우선, 없으면 symbols)
 *  3. per_symbol_contribution 테이블 (종목, 거래수, 수익률, 기여도)
 *  4. 파라미터 JSON pretty 출력
 *
 * 닫기 트리거: ✕ 버튼 또는 백드롭 클릭.
 */
import { useEffect, useMemo } from 'react'

function formatDate(iso) {
  if (!iso) return '-'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleString('ko-KR', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function formatPct(val, digits = 2) {
  if (val == null) return '-'
  const n = Number(val)
  if (Number.isNaN(n)) return '-'
  return `${n >= 0 ? '+' : ''}${n.toFixed(digits)}%`
}

function formatNumber(val) {
  if (val == null) return '-'
  const n = Number(val)
  if (Number.isNaN(n)) return '-'
  return n.toLocaleString('ko-KR')
}

/**
 * per_symbol_contribution 정규화 — backend에서 다양한 shape 응답 가능.
 *  - dict: { "005930": {symbol, trades, realized_pnl, wins, losses, return_pct, contribution_pct}, ... }
 *  - list: [{symbol, ...}]
 *
 * 반환: list of rows
 */
function normalizeContribution(raw) {
  if (!raw) return []
  if (Array.isArray(raw)) return raw
  if (typeof raw === 'object') {
    return Object.entries(raw).map(([code, v]) => ({
      symbol: code,
      ...(typeof v === 'object' ? v : {}),
    }))
  }
  return []
}

export default function BacktestPortfolioModal({ job, onClose }) {
  // ESC 키 닫기
  useEffect(() => {
    const onKey = (e) => {
      if (e.key === 'Escape' && onClose) onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  // 종목 이름 매핑: symbols_names 우선 → fallback symbols
  const symbolEntries = useMemo(() => {
    const named = Array.isArray(job?.symbols_names) ? job.symbols_names : null
    if (named && named.length > 0) {
      return named.map((e) => ({
        code: e.code || '',
        name: e.name || e.code || '',
      }))
    }
    const codes = Array.isArray(job?.symbols) ? job.symbols : []
    return codes.map((c) => ({ code: c, name: c }))
  }, [job])

  const result = job?.result_json || {}
  const contributions = useMemo(
    () => normalizeContribution(result.per_symbol_contribution),
    [result.per_symbol_contribution],
  )

  // 종목별 이름 룩업
  const nameByCode = useMemo(() => {
    const m = new Map()
    for (const e of symbolEntries) m.set(e.code, e.name)
    return m
  }, [symbolEntries])

  if (!job) return null

  const params = job.params_json || result.params || {}
  const strategyLabel = job.strategy_display_name || job.strategy_name || '-'
  const periodText = (job.start_date || result.start_date) && (job.end_date || result.end_date)
    ? `${job.start_date || result.start_date} ~ ${job.end_date || result.end_date}`
    : '-'

  const handleBackdrop = (e) => {
    if (e.target === e.currentTarget && onClose) onClose()
  }

  return (
    <div
      onClick={handleBackdrop}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      role="dialog"
      aria-modal="true"
      aria-label="포트폴리오 백테스트 상세"
    >
      <div className="bg-white rounded-xl shadow-xl max-w-3xl w-full max-h-[90vh] overflow-y-auto">
        {/* 헤더 */}
        <div className="flex items-start justify-between px-5 py-4 border-b border-gray-200">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="px-2 py-0.5 rounded text-xs font-medium bg-indigo-100 text-indigo-700">
                포트폴리오
              </span>
              <h2 className="text-base font-bold text-gray-900">
                {strategyLabel}
              </h2>
            </div>
            <div className="text-xs text-gray-500 space-y-0.5">
              <div>
                <span className="font-medium">실행 일시</span>:{' '}
                {formatDate(job.completed_at || job.submitted_at)}
              </div>
              <div>
                <span className="font-medium">기간</span>: {periodText}
              </div>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-700 text-xl leading-none"
            aria-label="닫기"
          >
            &times;
          </button>
        </div>

        {/* 핵심 메트릭 */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 px-5 py-4 bg-gray-50 border-b border-gray-200">
          <div>
            <div className="text-[10px] text-gray-500">최종 수익률</div>
            <div className={`text-sm font-mono font-bold ${
              job.total_return_pct > 0 ? 'text-red-600'
              : job.total_return_pct < 0 ? 'text-blue-600' : 'text-gray-700'
            }`}>
              {formatPct(job.total_return_pct, 2)}
            </div>
          </div>
          <div>
            <div className="text-[10px] text-gray-500">CAGR</div>
            <div className="text-sm font-mono font-bold text-gray-700">
              {formatPct(job.cagr, 2)}
            </div>
          </div>
          <div>
            <div className="text-[10px] text-gray-500">샤프</div>
            <div className="text-sm font-mono font-bold text-gray-700">
              {job.sharpe_ratio != null ? Number(job.sharpe_ratio).toFixed(2) : '-'}
            </div>
          </div>
          <div>
            <div className="text-[10px] text-gray-500">최대 낙폭</div>
            <div className="text-sm font-mono font-bold text-blue-600">
              {job.max_drawdown != null ? `-${Number(job.max_drawdown).toFixed(2)}%` : '-'}
            </div>
          </div>
        </div>

        {/* 섹션 1: 종목 칩 리스트 */}
        <div className="px-5 py-4 border-b border-gray-200">
          <h3 className="text-xs font-semibold text-gray-600 mb-2">
            구성 종목 ({symbolEntries.length}종목)
          </h3>
          <div className="flex flex-wrap gap-1.5">
            {symbolEntries.map((e) => (
              <span
                key={e.code}
                className="inline-flex items-center gap-1 bg-gray-100 text-gray-700 text-xs rounded-full px-2.5 py-1"
              >
                <span className="font-medium">{e.name}</span>
                {e.name !== e.code && (
                  <span className="font-mono text-[10px] text-gray-400">{e.code}</span>
                )}
              </span>
            ))}
          </div>
        </div>

        {/* 섹션 2: 종목별 기여도 테이블 */}
        <div className="px-5 py-4 border-b border-gray-200">
          <h3 className="text-xs font-semibold text-gray-600 mb-2">종목별 기여도</h3>
          {contributions.length === 0 ? (
            <div className="text-xs text-gray-400 py-3 text-center">
              종목별 기여도 데이터가 없습니다
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-gray-200 text-gray-500">
                    <th className="py-1.5 px-2 text-left font-medium">종목</th>
                    <th className="py-1.5 px-2 text-right font-medium">거래수</th>
                    <th className="py-1.5 px-2 text-right font-medium">수익률</th>
                    <th className="py-1.5 px-2 text-right font-medium">실현손익</th>
                    <th className="py-1.5 px-2 text-right font-medium">기여도</th>
                  </tr>
                </thead>
                <tbody>
                  {contributions.map((c) => {
                    const code = c.symbol || c.code || '-'
                    const name = nameByCode.get(code) || code
                    const ret = c.return_pct ?? c.total_return_pct
                    const contrib = c.contribution_pct ?? c.contribution
                    const pnl = c.realized_pnl ?? c.pnl
                    return (
                      <tr key={code} className="border-b border-gray-100">
                        <td className="py-1.5 px-2">
                          <div className="text-gray-900">{name}</div>
                          {name !== code && (
                            <div className="font-mono text-[10px] text-gray-400">{code}</div>
                          )}
                        </td>
                        <td className="py-1.5 px-2 text-right font-mono">
                          {c.trades != null ? c.trades : '-'}
                        </td>
                        <td className={`py-1.5 px-2 text-right font-mono ${
                          ret > 0 ? 'text-red-600' : ret < 0 ? 'text-blue-600' : ''
                        }`}>
                          {formatPct(ret, 2)}
                        </td>
                        <td className="py-1.5 px-2 text-right font-mono">
                          {pnl != null ? formatNumber(Math.floor(pnl)) : '-'}
                        </td>
                        <td className={`py-1.5 px-2 text-right font-mono ${
                          contrib > 0 ? 'text-red-600' : contrib < 0 ? 'text-blue-600' : ''
                        }`}>
                          {formatPct(contrib, 2)}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* 섹션 3: 파라미터 JSON */}
        <div className="px-5 py-4">
          <h3 className="text-xs font-semibold text-gray-600 mb-2">파라미터</h3>
          {Object.keys(params).length === 0 ? (
            <div className="text-xs text-gray-400 py-2">파라미터 없음</div>
          ) : (
            <pre className="text-[11px] font-mono bg-gray-50 border border-gray-200 rounded p-3 overflow-x-auto whitespace-pre-wrap">
              {JSON.stringify(params, null, 2)}
            </pre>
          )}
        </div>

        {/* 푸터 */}
        <div className="flex justify-end px-5 py-3 border-t border-gray-200 bg-gray-50">
          <button
            onClick={onClose}
            className="px-4 py-1.5 bg-white border border-gray-300 text-gray-700 text-sm rounded-md hover:bg-gray-100 transition-colors"
          >
            닫기
          </button>
        </div>
      </div>
    </div>
  )
}
