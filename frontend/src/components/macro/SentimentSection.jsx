import { ResponsiveContainer, AreaChart, Area } from 'recharts'
import LoadingSpinner from '../common/LoadingSpinner'
import ErrorAlert from '../common/ErrorAlert'

const VIX_COLORS = { low: '#22c55e', normal: '#eab308', high: '#f97316', extreme: '#ef4444' }
const VIX_LABELS = { low: '낮음', normal: '보통', high: '높음', extreme: '극단' }

const BUFFETT_COLORS = { undervalued: '#22c55e', fair: '#3b82f6', overvalued: '#f97316', significantly_overvalued: '#ef4444' }

function VixCard({ vix }) {
  if (!vix) return <EmptyCard title="VIX" />
  const color = VIX_COLORS[vix.level] || '#6b7280'
  const chartData = (vix.sparkline || []).map((v, i) => ({ i, v }))

  return (
    <div className="rounded-lg border bg-white p-4 shadow-sm">
      <div className="text-sm font-medium text-gray-500 mb-1">VIX (변동성 지수)</div>
      <div className="flex items-baseline gap-2">
        <span className="text-3xl font-bold" style={{ color }}>{vix.value}</span>
        <span className="text-sm" style={{ color: vix.change > 0 ? '#ef4444' : '#3b82f6' }}>
          {vix.change > 0 ? '+' : ''}{vix.change}
        </span>
      </div>
      <span
        className="inline-block mt-1 px-2 py-0.5 rounded text-xs font-medium text-white"
        style={{ backgroundColor: color }}
      >
        {VIX_LABELS[vix.level] || vix.level}
      </span>
      {chartData.length > 0 && (
        <div className="mt-2 h-10">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData}>
              <Area type="monotone" dataKey="v" stroke={color} strokeWidth={1.5} fill={color} fillOpacity={0.1} dot={false} isAnimationActive={false} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  )
}

function BuffettCard({ data }) {
  if (!data) return <EmptyCard title="버핏 지수" />
  const color = BUFFETT_COLORS[data.level] || '#6b7280'
  const pct = Math.min(data.ratio, 250) / 250 * 100

  return (
    <div className="rounded-lg border bg-white p-4 shadow-sm">
      <div className="text-sm font-medium text-gray-500 mb-1">버핏 지수</div>
      <div className="text-3xl font-bold" style={{ color }}>{data.ratio}%</div>
      <div className="text-xs text-gray-500 mt-1">
        시총 ${data.market_cap_t}T / GDP ${data.gdp_t}T
      </div>
      <div className="mt-2 h-3 bg-gray-100 rounded-full overflow-hidden">
        <div className="h-full rounded-full transition-all" style={{ width: `${pct}%`, backgroundColor: color }} />
      </div>
      <div className="flex justify-between text-xs text-gray-400 mt-1">
        <span>저평가</span><span>적정</span><span>고평가</span>
      </div>
    </div>
  )
}

function FearGreedCard({ data }) {
  if (!data) return <EmptyCard title="공포탐욕 지수" />
  const score = data.score
  const hue = score * 1.2 // 0=red, 120=green
  const color = `hsl(${hue}, 70%, 45%)`

  return (
    <div className="rounded-lg border bg-white p-4 shadow-sm">
      <div className="text-sm font-medium text-gray-500 mb-1">공포탐욕 지수</div>
      <div className="flex items-baseline gap-2">
        <span className="text-3xl font-bold" style={{ color }}>{score}</span>
        <span className="text-sm font-medium" style={{ color }}>{data.label}</span>
      </div>
      <div className="mt-3 h-4 rounded-full overflow-hidden" style={{
        background: 'linear-gradient(to right, #ef4444, #f97316, #eab308, #22c55e, #16a34a)'
      }}>
        <div className="relative h-full">
          <div
            className="absolute top-0 w-3 h-full bg-white border-2 border-gray-800 rounded-full -translate-x-1/2"
            style={{ left: `${score}%` }}
          />
        </div>
      </div>
      <div className="flex justify-between text-xs text-gray-400 mt-1">
        <span>극공포</span><span>중립</span><span>극탐욕</span>
      </div>
      {data.components && (
        <div className="mt-3 space-y-1 text-xs text-gray-500">
          <div className="flex justify-between"><span>VIX</span><span>{data.components.vix_score}</span></div>
          <div className="flex justify-between"><span>모멘텀</span><span>{data.components.momentum_score}</span></div>
          <div className="flex justify-between"><span>시장폭</span><span>{data.components.breadth_score}</span></div>
        </div>
      )}
    </div>
  )
}

function EmptyCard({ title }) {
  return (
    <div className="rounded-lg border bg-white p-4 shadow-sm">
      <div className="text-sm font-medium text-gray-500 mb-1">{title}</div>
      <div className="text-gray-400 text-sm">데이터 없음</div>
    </div>
  )
}

export default function SentimentSection({ data, loading, error }) {
  if (loading) return <LoadingSpinner message="심리 지표 로딩 중..." />
  if (error) return <ErrorAlert message={error} />
  if (!data) return null

  return (
    <section>
      <h2 className="text-lg font-semibold text-gray-900 mb-3">시장 심리</h2>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <FearGreedCard data={data.fear_greed} />
        <VixCard vix={data.vix} />
        <BuffettCard data={data.buffett_indicator} />
      </div>
    </section>
  )
}
