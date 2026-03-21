import { useNavigate } from 'react-router-dom'
import SparklineChart from './SparklineChart'

function fmt(n) {
  if (n == null) return '-'
  return n.toLocaleString()
}

function fmtMktcap(v) {
  if (!v) return '-'
  const oc = Math.round(v / 100000000)
  if (oc >= 10000) return `${(oc / 10000).toFixed(1)}조`
  return `${oc.toLocaleString()}억`
}

/**
 * MarketBoardCard
 * stock: { code, name, market_type, price, change_pct, mktcap, year_high, year_low }
 * livePrice: { price, change_pct, sign } (WS 실시간)
 * sparkline: [{date, close}]
 * badge: 'high' | 'low' (신고가/신저가 배지)
 */
export default function MarketBoardCard({ stock, livePrice, sparkline, badge }) {
  const navigate = useNavigate()
  if (!stock) return null

  const price   = livePrice?.price    ?? stock.price
  const chgPct  = livePrice?.change_pct ?? stock.change_pct
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

      {/* 가격 + 등락 */}
      <div className="flex items-baseline gap-1.5 mb-1">
        <span className="text-sm font-bold text-white">{fmt(price)}</span>
        <span className={`text-xs font-medium ${chgCls}`}>
          {chgPct != null ? `${chgPct > 0 ? '+' : ''}${chgPct.toFixed(2)}%` : '-'}
        </span>
      </div>

      {/* 미니 차트 */}
      <SparklineChart data={sparkline} trend={trend} height={32} />
    </div>
  )
}
