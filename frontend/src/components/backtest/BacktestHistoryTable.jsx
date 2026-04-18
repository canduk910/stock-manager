/**
 * 백테스트 이력 테이블.
 * 과거 실행 결과 목록 + 한글 전략명 + 카테고리 배지 + 삭제 + "보기" 버튼.
 */
import { CATEGORY_LABELS, CATEGORY_COLORS } from './StrategySelector'

const STATUS_BADGE = {
  completed: 'bg-green-100 text-green-800',
  submitted: 'bg-yellow-100 text-yellow-800',
  failed: 'bg-red-100 text-red-800',
}

const STRATEGY_KR = {
  sma_crossover: '이동평균 교차',
  ema_crossover: 'EMA 교차',
  momentum: '모멘텀',
  rsi_reversal: 'RSI 역추세',
  bollinger_breakout: '볼린저 돌파',
  macd_signal: 'MACD 시그널',
  volatility_breakout: '변동성 돌파',
  mean_reversion: '평균회귀',
  trend_filter_signal: '추세 필터',
  dual_momentum: '듀얼 모멘텀',
  custom: '커스텀',
}

const STRATEGY_CATEGORY = {
  sma_crossover: 'trend',
  ema_crossover: 'trend',
  momentum: 'momentum',
  rsi_reversal: 'mean_reversion',
  bollinger_breakout: 'volatility',
  macd_signal: 'trend',
  volatility_breakout: 'volatility',
  mean_reversion: 'mean_reversion',
  trend_filter_signal: 'composite',
  dual_momentum: 'momentum',
}

function formatDate(iso) {
  if (!iso) return '-'
  const d = new Date(iso)
  return d.toLocaleDateString('ko-KR', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

function formatPct(val) {
  if (val == null) return '-'
  const n = Number(val)
  return isNaN(n) ? '-' : `${n >= 0 ? '+' : ''}${n.toFixed(1)}%`
}

export default function BacktestHistoryTable({ history, onSelect, onDelete, loading }) {
  if (loading) {
    return <div className="text-sm text-gray-500 py-4 text-center">이력 로딩 중...</div>
  }

  if (!history || history.length === 0) {
    return <div className="text-sm text-gray-400 py-4 text-center">백테스트 이력이 없습니다</div>
  }

  const handleDelete = (e, jobId) => {
    e.stopPropagation()
    if (onDelete) onDelete(jobId)
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-200 text-gray-500 text-xs">
            <th className="py-2 px-2 text-left font-medium">일시</th>
            <th className="py-2 px-2 text-left font-medium">종목</th>
            <th className="py-2 px-2 text-left font-medium">카테고리</th>
            <th className="py-2 px-2 text-left font-medium">전략</th>
            <th className="py-2 px-2 text-right font-medium">수익률</th>
            <th className="py-2 px-2 text-right font-medium">샤프</th>
            <th className="py-2 px-2 text-right font-medium">낙폭</th>
            <th className="py-2 px-2 text-center font-medium">상태</th>
            <th className="py-2 px-2 text-center font-medium"></th>
            <th className="py-2 px-2 text-center font-medium"></th>
          </tr>
        </thead>
        <tbody>
          {history.map((job) => {
            const isStale = job.status === 'submitted' &&
              new Date() - new Date(job.submitted_at) > 10 * 60 * 1000
            const displayStatus = isStale ? 'failed' : job.status
            const category = STRATEGY_CATEGORY[job.strategy_name]
            const symbolDisplay = job.symbol_name && job.symbol_name !== job.symbol
              ? `${job.symbol_name}`
              : job.symbol

            return (
              <tr key={job.job_id} className="border-b border-gray-100 hover:bg-gray-50">
                <td className="py-2 px-2 text-gray-600 whitespace-nowrap">
                  {formatDate(job.submitted_at || job.completed_at)}
                </td>
                <td className="py-2 px-2">
                  <div className="font-medium text-gray-900">{symbolDisplay}</div>
                  {job.symbol_name && job.symbol_name !== job.symbol && (
                    <div className="text-xs text-gray-400 font-mono">{job.symbol}</div>
                  )}
                </td>
                <td className="py-2 px-2">
                  {category && (
                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${CATEGORY_COLORS[category] || 'bg-gray-100 text-gray-600'}`}>
                      {CATEGORY_LABELS[category] || category}
                    </span>
                  )}
                </td>
                <td className="py-2 px-2">
                  {STRATEGY_KR[job.strategy_name] || job.strategy_name}
                </td>
                <td className="py-2 px-2 text-right font-mono">
                  <span className={job.total_return_pct > 0 ? 'text-red-600' : job.total_return_pct < 0 ? 'text-blue-600' : ''}>
                    {formatPct(job.total_return_pct)}
                  </span>
                </td>
                <td className="py-2 px-2 text-right font-mono">
                  {job.sharpe_ratio != null ? Number(job.sharpe_ratio).toFixed(2) : '-'}
                </td>
                <td className="py-2 px-2 text-right font-mono text-blue-600">
                  {job.max_drawdown != null ? `-${Number(job.max_drawdown).toFixed(1)}%` : '-'}
                </td>
                <td className="py-2 px-2 text-center">
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_BADGE[displayStatus] || 'bg-gray-100 text-gray-600'}`}>
                    {isStale ? '시간초과' : displayStatus === 'completed' ? '완료' : displayStatus === 'submitted' ? '실행중' : '실패'}
                  </span>
                </td>
                <td className="py-2 px-2 text-center">
                  {onDelete && (
                    <button
                      onClick={(e) => handleDelete(e, job.job_id)}
                      className="text-xs text-gray-400 hover:text-red-600 transition-colors"
                      title="삭제"
                    >
                      &times;
                    </button>
                  )}
                </td>
                <td className="py-2 px-2 text-center">
                  {job.status === 'completed' && (
                    <button
                      onClick={() => onSelect(job)}
                      className="text-xs text-blue-600 hover:text-blue-800 hover:underline"
                    >
                      보기
                    </button>
                  )}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
