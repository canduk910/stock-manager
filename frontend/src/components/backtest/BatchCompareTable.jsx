/**
 * 배치 백테스트 전략 비교 테이블.
 */
const PRESET_LABELS = {
  sma_crossover: 'SMA 크로스',
  momentum: '모멘텀',
  trend_filter_signal: '추세 필터',
  week52_high: '52주 신고가',
  ma_divergence: '이격도',
  false_breakout: '돌파 실패',
  short_term_reversal: '단기 반전',
  strong_close: '강한 종가',
  volatility_breakout: '변동성 돌파',
  consecutive_moves: '연속 캔들',
}

export default function BatchCompareTable({ result }) {
  if (!result) return null

  const runs = result.runs || result.results || []
  if (runs.length === 0) return null

  return (
    <div className="bg-white rounded-lg border p-4">
      <h3 className="text-sm font-medium text-gray-700 mb-3">전략 비교 ({runs.length}개)</h3>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-3 py-2 text-left">전략</th>
              <th className="px-3 py-2 text-right">수익률</th>
              <th className="px-3 py-2 text-right">샤프</th>
              <th className="px-3 py-2 text-right">낙폭</th>
              <th className="px-3 py-2 text-right">승률</th>
              <th className="px-3 py-2 text-right">거래수</th>
              <th className="px-3 py-2 text-center">상태</th>
            </tr>
          </thead>
          <tbody>
            {runs.map((run, i) => {
              const m = run.metrics || {}
              const name = run.preset || run.strategy_name || run.strategy_id || `전략 ${i + 1}`
              return (
                <tr key={i} className="border-t hover:bg-gray-50">
                  <td className="px-3 py-2 font-medium">{PRESET_LABELS[name] || name}</td>
                  <td className={`px-3 py-2 text-right ${(m.total_return_pct || 0) >= 0 ? 'text-red-600' : 'text-blue-600'}`}>
                    {m.total_return_pct != null ? `${m.total_return_pct >= 0 ? '+' : ''}${m.total_return_pct.toFixed(1)}%` : '-'}
                  </td>
                  <td className="px-3 py-2 text-right">{m.sharpe_ratio?.toFixed(2) ?? '-'}</td>
                  <td className="px-3 py-2 text-right">{m.max_drawdown != null ? `${m.max_drawdown.toFixed(1)}%` : '-'}</td>
                  <td className="px-3 py-2 text-right">{m.win_rate != null ? `${m.win_rate.toFixed(1)}%` : '-'}</td>
                  <td className="px-3 py-2 text-right">{m.total_trades ?? '-'}</td>
                  <td className="px-3 py-2 text-center">
                    <span className={`px-2 py-0.5 rounded text-xs ${
                      run.status === 'completed' ? 'bg-green-100 text-green-700' :
                      run.status === 'failed' ? 'bg-red-100 text-red-700' :
                      'bg-yellow-100 text-yellow-700'
                    }`}>
                      {run.status === 'completed' ? '완료' : run.status === 'failed' ? '실패' : '실행중'}
                    </span>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
