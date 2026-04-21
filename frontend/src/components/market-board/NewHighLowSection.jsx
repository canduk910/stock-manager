import MarketBoardCard from './MarketBoardCard'

export default function NewHighLowSection({ data, sparklines, prices, ohlc }) {
  if (!data) return null
  const { new_highs = [], new_lows = [] } = data

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* 신고가 */}
      <div>
        <h2 className="text-base font-bold text-red-400 mb-3 flex items-center gap-2">
          <span>▲ 당일 신고가</span>
          <span className="text-xs text-gray-500 font-normal">(52주 최고, 시총 상위)</span>
        </h2>
        {new_highs.length === 0 ? (
          <p className="text-gray-500 text-sm py-8 text-center">해당 종목 없음</p>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 gap-2">
            {new_highs.map(stock => (
              <MarketBoardCard
                key={stock.code}
                stock={stock}
                livePrice={prices?.[stock.code]}
                sparkline={sparklines?.[stock.code]}
                ohlc={ohlc?.[stock.code]}
                badge="high"
              />
            ))}
          </div>
        )}
      </div>

      {/* 신저가 */}
      <div>
        <h2 className="text-base font-bold text-blue-400 mb-3 flex items-center gap-2">
          <span>▼ 당일 신저가</span>
          <span className="text-xs text-gray-500 font-normal">(52주 최저, 시총 상위)</span>
        </h2>
        {new_lows.length === 0 ? (
          <p className="text-gray-500 text-sm py-8 text-center">해당 종목 없음</p>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 gap-2">
            {new_lows.map(stock => (
              <MarketBoardCard
                key={stock.code}
                stock={stock}
                livePrice={prices?.[stock.code]}
                sparkline={sparklines?.[stock.code]}
                ohlc={ohlc?.[stock.code]}
                badge="low"
              />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
