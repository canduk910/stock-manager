import { useNavigate } from 'react-router-dom'
import SparklineChart from './SparklineChart'
import MiniCandleBar from './MiniCandleBar'

function fmt(n) {
  if (n == null) return '-'
  return n.toLocaleString()
}

/**
 * MarketBoardCard
 * stock: { code, name, market_type, price, change_pct, mktcap, year_high, year_low }
 * livePrice: { price, change_pct, change, sign, open, high, low } (WS 실시간)
 * sparkline: [{date, close}]
 * ohlc: { open, high, low, close, prev_close } (REST 당일 OHLC)
 * badge: 'high' | 'low' (신고가/신저가 배지)
 */
export default function MarketBoardCard({ stock, livePrice, sparkline, ohlc, badge }) {
  const navigate = useNavigate()
  if (!stock) return null

  const price   = livePrice?.price    ?? stock.price
  const chgPct  = livePrice?.change_pct ?? stock.change_pct

  // 전일대비 가격: WS 우선 → ohlc 기반 계산 fallback
  const change  = livePrice?.change
    ?? (ohlc?.prev_close && price ? Math.round(price - ohlc.prev_close) : null)

  // 당일 OHLC: WS 우선 → REST fallback
  const dayOpen = livePrice?.open  ?? ohlc?.open
  const dayHigh = livePrice?.high  ?? ohlc?.high
  const dayLow  = livePrice?.low   ?? ohlc?.low

  const isUp    = chgPct > 0
  const isDown  = chgPct < 0
  const chgCls  = isUp ? 'text-red-400' : isDown ? 'text-blue-400' : 'text-gray-400'
  const trend   = isUp ? 'up' : isDown ? 'down' : null

  return (
    <div
      className="bg-gray-800 rounded-xl p-2 cursor-pointer hover:bg-gray-750 hover:ring-1 hover:ring-gray-600 transition-all"
      onClick={() => navigate(`/detail/${stock.code}`)}
    >
      {/* 헤더: 종목명 + 배지 + 시장 */}
      <div className="flex items-start justify-between mb-1 gap-1">
        <div className="flex items-center gap-1 min-w-0">
          {badge === 'high' && (
            <span className="shrink-0 px-1 py-0.5 text-[9px] font-bold bg-red-900 text-red-300 rounded">신고가</span>
          )}
          {badge === 'low' && (
            <span className="shrink-0 px-1 py-0.5 text-[9px] font-bold bg-blue-900 text-blue-300 rounded">신저가</span>
          )}
          <span className="text-xs font-semibold text-white truncate">{stock.name}</span>
        </div>
        <span className="shrink-0 text-[10px] text-gray-500 mt-0.5">{stock.market_type}</span>
      </div>

      {/* 가격 + 전일대비 + 등락률 */}
      <div className="flex items-baseline gap-1 mb-1 flex-wrap">
        <span className="text-sm font-bold text-white">{fmt(price)}</span>
        {change != null && (
          <span className={`text-[10px] font-medium ${chgCls}`}>
            ({change > 0 ? '+' : ''}{fmt(change)})
          </span>
        )}
        <span className={`text-[10px] font-medium ${chgCls}`}>
          {chgPct != null ? `${chgPct > 0 ? '+' : ''}${chgPct.toFixed(2)}%` : '-'}
        </span>
      </div>

      {/* 차트 영역: 스파크라인(~80%) + 미니캔들(~20%) */}
      <div className="flex items-center gap-1 mb-1">
        <div className="flex-1 min-w-0">
          <SparklineChart data={sparkline} trend={trend} height={28} />
        </div>
        <MiniCandleBar open={dayOpen} high={dayHigh} low={dayLow} close={price} />
      </div>

      {/* 당일 고가 / 저가 */}
      {(dayHigh != null || dayLow != null) && (
        <div className="flex items-center gap-1.5 text-[9px] text-gray-500">
          {dayHigh != null && <span>H <span className="text-red-400/70">{fmt(dayHigh)}</span></span>}
          {dayHigh != null && dayLow != null && <span>·</span>}
          {dayLow != null && <span>L <span className="text-blue-400/70">{fmt(dayLow)}</span></span>}
        </div>
      )}
    </div>
  )
}
