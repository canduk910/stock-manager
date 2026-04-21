/**
 * 당일 일중 가격변동 미니 캔들.
 * CSS 기반 단일 캔들 (Recharts 불필요).
 */
export default function MiniCandleBar({ open, high, low, close }) {
  if (!open || !high || !low || !close) return null
  const range = high - low
  if (range <= 0) return null

  const isUp = close >= open
  const color = isUp ? '#ef4444' : '#3b82f6'

  const bodyTop = Math.max(open, close)
  const bodyBot = Math.min(open, close)

  // 비율 계산 (top→bottom 순서로 렌더링)
  const wickTopPct = ((high - bodyTop) / range) * 100
  const bodyPct = Math.max(((bodyTop - bodyBot) / range) * 100, 6) // 최소 6%
  const wickBotPct = ((bodyBot - low) / range) * 100

  return (
    <div className="flex flex-col items-center" style={{ height: 28, width: 14 }}>
      {/* 윗꼬리 */}
      <div style={{ width: 1.5, flexBasis: `${wickTopPct}%`, flexShrink: 0, backgroundColor: color }} />
      {/* 몸통 */}
      <div style={{ width: 7, flexBasis: `${bodyPct}%`, flexShrink: 0, backgroundColor: color, borderRadius: 1 }} />
      {/* 아래꼬리 */}
      <div style={{ width: 1.5, flexBasis: `${wickBotPct}%`, flexShrink: 0, backgroundColor: color }} />
    </div>
  )
}
