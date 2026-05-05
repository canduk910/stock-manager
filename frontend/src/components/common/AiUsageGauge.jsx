import { useAiUsage } from '../../hooks/useAiUsage'

export default function AiUsageGauge() {
  const { usage } = useAiUsage()

  if (!usage || !Number.isFinite(usage.limit) || usage.limit <= 0) return null

  const used = Math.max(0, usage.used || 0)
  const limit = usage.limit
  const remaining = Math.max(0, usage.remaining ?? limit - used)
  const ratio = Math.min(1, used / limit)
  const pct = Math.round(ratio * 100)

  let barColor = 'bg-emerald-400'
  if (ratio >= 0.95) barColor = 'bg-red-500'
  else if (ratio >= 0.8) barColor = 'bg-amber-400'
  else if (ratio >= 0.5) barColor = 'bg-indigo-400'

  return (
    <div
      className="hidden sm:flex items-center gap-2 px-2 py-1 rounded text-xs"
      title={`오늘 AI 호출 사용량 ${used}/${limit} · 남은 횟수 ${remaining}`}
      aria-label={`AI 사용량 ${used}/${limit}`}
    >
      <span className="text-gray-400">AI</span>
      <div className="w-24 h-1.5 rounded-full bg-gray-700 overflow-hidden">
        <div
          className={`h-full ${barColor} transition-all`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-gray-300 tabular-nums">
        {used}<span className="text-gray-500">/{limit}</span>
      </span>
    </div>
  )
}
