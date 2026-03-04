/**
 * 실시간 호가창 컴포넌트.
 * 국내(KR): KIS WS 기반 10호가 + 현재가
 * 해외(US): yfinance polling 현재가만 (호가 미지원)
 *
 * Props:
 *   symbol      - 종목코드 (예: '005930', 'AAPL')
 *   market      - 'KR' | 'US'
 *   onPriceSelect(price) - 호가 클릭 시 가격 전달 콜백
 */
import { useQuote } from '../../hooks/useQuote'

function formatPrice(price, market) {
  if (price == null || price === 0) return '—'
  if (market === 'US') return price.toFixed(2)
  return Math.floor(price).toLocaleString()
}

function formatVolume(vol) {
  if (vol == null || vol === 0) return ''
  if (vol >= 10000) return `${(vol / 10000).toFixed(1)}만`
  return vol.toLocaleString()
}

// 잔량 최대값 대비 비율 계산 (배경바 너비)
function calcPct(volume, maxVolume) {
  if (!maxVolume || !volume) return 0
  return Math.min((volume / maxVolume) * 100, 100)
}

export default function OrderbookPanel({ symbol, market = 'KR', onPriceSelect }) {
  const { price, change, changeRate, sign, asks, bids, totalAskVolume, totalBidVolume, connected } = useQuote(symbol)

  const isDomestic = market === 'KR'

  // 가격 등락 색상: sign '2'=상승(빨강), '5'=하락(파랑), '3'=보합(회색)
  const priceColor =
    sign === '2' ? 'text-red-600' :
    sign === '5' ? 'text-blue-600' :
    change > 0 ? 'text-red-600' :
    change < 0 ? 'text-blue-600' :
    'text-gray-700'

  const changeLabel = change != null ? (
    <span className={priceColor}>
      {change >= 0 ? '▲' : '▼'} {formatPrice(Math.abs(change), market)}
      {changeRate != null && ` (${Math.abs(changeRate).toFixed(2)}%)`}
    </span>
  ) : null

  // asks[0]은 최우선(최저) 매도호가 → UI 상단은 높은가격 → reverse
  const displayAsks = isDomestic ? [...asks].reverse() : []
  const displayBids = isDomestic ? bids : []

  // 잔량 배경바 최대값 (매도/매수 통합)
  const allVolumes = [...displayAsks, ...displayBids].map((r) => r.volume).filter(Boolean)
  const maxVolume = allVolumes.length > 0 ? Math.max(...allVolumes) : 1

  // 종목 없음 플레이스홀더
  if (!symbol) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-6 flex flex-col items-center justify-center min-h-[400px] text-center">
        <div className="text-gray-300 text-4xl mb-3">📊</div>
        <p className="text-sm text-gray-400">종목코드를 입력하면<br />호가창이 표시됩니다</p>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      {/* 헤더 */}
      <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-sm font-bold text-gray-800">{symbol}</span>
          <span className={`inline-flex items-center gap-1 text-xs ${connected ? 'text-green-500' : 'text-gray-400'}`}>
            <span className={`w-1.5 h-1.5 rounded-full ${connected ? 'bg-green-500' : 'bg-gray-300'}`} />
            {connected ? '실시간' : '연결 중...'}
          </span>
        </div>
        {!isDomestic && (
          <span className="text-xs text-gray-400 bg-gray-50 px-2 py-0.5 rounded">15분 지연</span>
        )}
      </div>

      {/* 현재가 */}
      <div className="px-4 py-3 bg-gray-50 border-b border-gray-100">
        {price != null ? (
          <div>
            <div className={`text-2xl font-bold ${priceColor}`}>
              {formatPrice(price, market)}
              <span className="text-sm font-normal ml-1">{market === 'KR' ? '원' : 'USD'}</span>
            </div>
            {changeLabel && <div className="text-sm mt-0.5">{changeLabel}</div>}
          </div>
        ) : (
          <div className="text-gray-400 text-sm">시세 로딩 중...</div>
        )}
      </div>

      {/* 호가 테이블 */}
      {isDomestic ? (
        <div className="text-xs">
          {/* 컬럼 헤더 */}
          <div className="grid grid-cols-3 text-center text-gray-400 font-medium py-1.5 border-b border-gray-100 bg-gray-50">
            <span className="text-blue-400">잔량(매도)</span>
            <span>가격</span>
            <span className="text-red-400">잔량(매수)</span>
          </div>

          {/* 매도 10호가 (높은가격→낮은가격, 위→아래) */}
          {displayAsks.map((row, i) => {
            const pct = calcPct(row.volume, maxVolume)
            return (
              <div
                key={`ask-${i}`}
                onClick={() => row.price > 0 && onPriceSelect?.(row.price)}
                className="grid grid-cols-3 text-center py-1 hover:bg-blue-50 cursor-pointer border-b border-gray-50 relative"
              >
                {/* 잔량 배경바 (왼쪽 정렬) */}
                <div className="relative flex items-center justify-end pr-2 z-10">
                  <div
                    className="absolute right-0 top-0 bottom-0 bg-blue-50 opacity-80"
                    style={{ width: `${pct}%` }}
                  />
                  <span className="relative text-blue-600 font-medium">{formatVolume(row.volume)}</span>
                </div>
                {/* 가격 */}
                <div className="text-blue-700 font-medium z-10">
                  {formatPrice(row.price, market)}
                </div>
                <div />
              </div>
            )
          })}

          {/* 현재가 구분선 */}
          {price != null && (
            <div
              onClick={() => onPriceSelect?.(Math.floor(price))}
              className="grid grid-cols-3 text-center py-1.5 bg-gray-100 border-y border-gray-200 cursor-pointer hover:bg-gray-150"
            >
              <div />
              <div className={`font-bold ${priceColor}`}>
                {formatPrice(price, market)}
              </div>
              <div />
            </div>
          )}

          {/* 매수 10호가 (높은가격→낮은가격, 위→아래) */}
          {displayBids.map((row, i) => {
            const pct = calcPct(row.volume, maxVolume)
            return (
              <div
                key={`bid-${i}`}
                onClick={() => row.price > 0 && onPriceSelect?.(row.price)}
                className="grid grid-cols-3 text-center py-1 hover:bg-red-50 cursor-pointer border-b border-gray-50 relative"
              >
                <div />
                {/* 가격 */}
                <div className="text-red-700 font-medium z-10">
                  {formatPrice(row.price, market)}
                </div>
                {/* 잔량 배경바 (오른쪽 정렬) */}
                <div className="relative flex items-center justify-start pl-2 z-10">
                  <div
                    className="absolute left-0 top-0 bottom-0 bg-red-50 opacity-80"
                    style={{ width: `${pct}%` }}
                  />
                  <span className="relative text-red-600 font-medium">{formatVolume(row.volume)}</span>
                </div>
              </div>
            )
          })}

          {/* 총잔량 푸터 */}
          {(totalAskVolume != null || totalBidVolume != null) && (
            <div className="grid grid-cols-3 text-center py-1.5 bg-gray-50 border-t border-gray-200 font-medium">
              <span className="text-blue-600">{formatVolume(totalAskVolume)}</span>
              <span className="text-gray-500">총잔량</span>
              <span className="text-red-600">{formatVolume(totalBidVolume)}</span>
            </div>
          )}

          {/* 호가 데이터 없을 때 안내 */}
          {displayAsks.length === 0 && displayBids.length === 0 && (
            <div className="py-8 text-center text-gray-400 text-xs">
              호가 데이터 수신 중...
            </div>
          )}
        </div>
      ) : (
        /* 해외주식: 호가 미지원 안내 */
        <div className="px-4 py-8 text-center">
          <p className="text-sm text-gray-400">해외주식 호가는 지원되지 않습니다</p>
          <p className="text-xs text-gray-300 mt-1">현재가만 2초 간격으로 업데이트됩니다</p>
        </div>
      )}
    </div>
  )
}
