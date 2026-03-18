import { useId } from 'react'
import { AreaChart, Area, ResponsiveContainer } from 'recharts'

/**
 * 미니 스파크라인 차트.
 * data: [{ date, close }, ...]
 * trend: 'up' | 'down' | null (색상 결정)
 */
export default function SparklineChart({ data = [], trend = null }) {
  const uid = useId()
  if (!data || data.length < 2) {
    return <div className="h-12 flex items-center justify-center text-gray-600 text-xs">-</div>
  }

  const color = trend === 'up' ? '#ef4444' : trend === 'down' ? '#3b82f6' : '#6b7280'

  return (
    <div className="h-12 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 2, right: 0, left: 0, bottom: 2 }}>
          <defs>
            <linearGradient id={`sparkGrad-${uid}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={color} stopOpacity={0.3} />
              <stop offset="95%" stopColor={color} stopOpacity={0} />
            </linearGradient>
          </defs>
          <Area
            type="monotone"
            dataKey="close"
            stroke={color}
            strokeWidth={1.5}
            fill={`url(#sparkGrad-${uid})`}
            dot={false}
            isAnimationActive={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}
