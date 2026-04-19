import { useMemo } from 'react'
import { computePositionSummary } from './backtestUtils'

function StatCard({ label, value, sub, color }) {
  return (
    <div className="bg-white rounded-lg border p-3 text-center">
      <div className="text-xs text-gray-500">{label}</div>
      <div className={`text-lg font-semibold ${color || ''}`}>{value}</div>
      {sub && <div className="text-[10px] text-gray-400 mt-0.5">{sub}</div>}
    </div>
  )
}

export default function PositionSummary({ trades }) {
  const summary = useMemo(() => computePositionSummary(trades), [trades])

  if (!summary) return null

  return (
    <div className="bg-white rounded-lg border p-4">
      <h3 className="text-sm font-medium text-gray-700 mb-3">포지션 요약</h3>
      <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
        <StatCard
          label="평균 보유 기간"
          value={summary.avgHoldingDays != null ? `${Math.round(summary.avgHoldingDays)}일` : '-'}
          sub={summary.longestHoldingDays != null
            ? `최장 ${summary.longestHoldingDays}일 / 최단 ${summary.shortestHoldingDays}일`
            : null}
        />
        <StatCard
          label="평균 수익 거래"
          value={summary.avgWinPct != null ? `+${summary.avgWinPct.toFixed(2)}%` : '-'}
          color="text-red-600"
          sub={`${summary.winCount}건 수익`}
        />
        <StatCard
          label="평균 손실 거래"
          value={summary.avgLossPct != null ? `${summary.avgLossPct.toFixed(2)}%` : '-'}
          color="text-blue-600"
          sub={`${summary.lossCount}건 손실`}
        />
        <StatCard
          label="최대 연속 수익"
          value={`${summary.maxConsecutiveWins}연승`}
          color="text-red-600"
        />
        <StatCard
          label="최대 연속 손실"
          value={`${summary.maxConsecutiveLosses}연패`}
          color="text-blue-600"
        />
        <StatCard
          label="승패 분포"
          value={`${summary.winCount}W / ${summary.lossCount}L`}
          sub={summary.winCount + summary.lossCount > 0
            ? `승률 ${((summary.winCount / (summary.winCount + summary.lossCount)) * 100).toFixed(1)}%`
            : null}
        />
      </div>
    </div>
  )
}
