/**
 * 백테스트 이력 테이블.
 * 과거 실행 결과 목록 + 전략명(MCP display name 우선) + 카테고리 배지 + 파라미터 + 삭제 + "보기".
 */
import { useState } from 'react'
import { CATEGORY_LABELS, CATEGORY_COLORS, PARAM_KR } from './StrategySelector'

const STATUS_BADGE = {
  completed: 'bg-green-100 text-green-800',
  submitted: 'bg-yellow-100 text-yellow-800',
  failed: 'bg-red-100 text-red-800',
}

/** 전략명 fallback 매핑 (strategy_display_name이 없는 레거시 데이터용) */
const STRATEGY_KR = {
  sma_crossover: 'SMA 크로스오버',
  momentum: '모멘텀 (ROC)',
  volatility_breakout: '변동성 돌파',
  false_breakout: '거짓 돌파',
  consecutive_moves: '연속 상승/하락',
  short_term_reversal: '단기 반전',
  ma_divergence: '이평선 이격도',
  week52_high: '52주 신고가',
  strong_close: '강한 종가 (IBS)',
  trend_filter_signal: '추세 필터 + 시그널',
  custom: '커스텀',
  builder: '빌더 전략',
}

const STRATEGY_CATEGORY = {
  sma_crossover: 'trend',
  momentum: 'momentum',
  volatility_breakout: 'volatility',
  false_breakout: 'mean_reversion',
  consecutive_moves: 'momentum',
  short_term_reversal: 'mean_reversion',
  ma_divergence: 'mean_reversion',
  week52_high: 'trend',
  strong_close: 'momentum',
  trend_filter_signal: 'trend',
  builder: 'composite',
  custom: 'composite',
}

/** 빌더/커스텀 전략 요약 정보 포맷 (indicators 배열이 있는 경우) */
function formatBuilderSummary(params) {
  if (!params || !Array.isArray(params.indicators)) return null
  const indicators = params.indicators
    .map((ind) => {
      const id = (ind.id || '').toUpperCase()
      const p = ind.params || {}
      const paramStr = Object.values(p).join(',')
      return paramStr ? `${id}(${paramStr})` : id
    })
    .filter(Boolean)
    .join(', ')
  const conditions = []
  if (params.entry_count != null) conditions.push(`진입 ${params.entry_count}개`)
  if (params.exit_count != null) conditions.push(`청산 ${params.exit_count}개`)
  const riskParts = []
  if (params.risk) {
    if (params.risk.stop_loss != null) riskParts.push(`손절 ${params.risk.stop_loss}%`)
    if (params.risk.take_profit != null) riskParts.push(`익절 ${params.risk.take_profit}%`)
    if (params.risk.trailing_stop != null) riskParts.push(`추적 ${params.risk.trailing_stop}%`)
  }
  return { indicators, conditions: conditions.join(' / '), risk: riskParts.join(' | ') }
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
  const [expandedJob, setExpandedJob] = useState(null)

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

  const toggleParams = (e, jobId) => {
    e.stopPropagation()
    setExpandedJob(expandedJob === jobId ? null : jobId)
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
              ? job.symbol_name : job.symbol
            // 전략명: MCP display name 우선 → STRATEGY_KR fallback → ID
            const strategyLabel = job.strategy_display_name
              || STRATEGY_KR[job.strategy_name]
              || job.strategy_name
            const params = job.params_json
            const hasParams = params && Object.keys(params).length > 0
            const isExpanded = expandedJob === job.job_id

            return (
              <tr key={job.job_id} className="border-b border-gray-100 hover:bg-gray-50 align-top">
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
                  <div>{strategyLabel}</div>
                  {hasParams && (() => {
                    const builderSummary = formatBuilderSummary(params)
                    return builderSummary ? (
                      <>
                        <button
                          onClick={(e) => toggleParams(e, job.job_id)}
                          className="text-[10px] text-gray-400 hover:text-blue-500 mt-0.5"
                        >
                          {isExpanded ? '전략 상세 ▲' : '전략 상세 ▼'}
                        </button>
                        {isExpanded && (
                          <div className="mt-1 space-y-0.5">
                            {builderSummary.indicators && (
                              <div className="text-[10px] text-gray-500">
                                <span className="font-medium">지표</span>: <span className="font-mono">{builderSummary.indicators}</span>
                              </div>
                            )}
                            {builderSummary.conditions && (
                              <div className="text-[10px] text-gray-500">
                                <span className="font-medium">조건</span>: {builderSummary.conditions}
                              </div>
                            )}
                            {builderSummary.risk && (
                              <div className="text-[10px] text-gray-500">
                                <span className="font-medium">리스크</span>: {builderSummary.risk}
                              </div>
                            )}
                          </div>
                        )}
                      </>
                    ) : (
                      <>
                        <button
                          onClick={(e) => toggleParams(e, job.job_id)}
                          className="text-[10px] text-gray-400 hover:text-blue-500 mt-0.5"
                        >
                          {isExpanded ? '파라미터 ▲' : '파라미터 ▼'}
                        </button>
                        {isExpanded && (
                          <div className="mt-1 space-y-0.5">
                            {Object.entries(params).map(([k, v]) => {
                              const kr = PARAM_KR[k]
                              return (
                                <div key={k} className="text-[10px] text-gray-500">
                                  <span className="font-medium">{kr?.label || k}</span>: <span className="font-mono">{typeof v === 'object' ? JSON.stringify(v) : v}</span>
                                  {kr?.desc && <span className="text-gray-400 ml-1">— {kr.desc}</span>}
                                </div>
                              )
                            })}
                          </div>
                        )}
                      </>
                    )
                  })()}
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
