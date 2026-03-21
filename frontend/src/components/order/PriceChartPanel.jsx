/**
 * 주문 페이지 가격 차트 패널.
 * 캔들스틱 + MA5/MA20 + 볼린저밴드 + 거래량.
 * RSI/MACD/Stochastic 없이 가격·거래량만 표시.
 *
 * Props:
 *   symbol  - 종목코드 (예: '005930', 'AAPL')
 *   market  - 'KR' | 'US'
 */
import { useState, useEffect, useRef } from 'react'
import { useAdvisoryOhlcv } from '../../hooks/useAdvisory'
import CandlestickChart, {
  INTERVAL_OPTS,
  PERIOD_OPTIONS,
} from '../common/CandlestickChart'

const DEFAULT_PERIOD = { '15m': '5d', '60m': '3mo', '1d': '3mo', '1wk': '1y' }

export default function PriceChartPanel({ symbol, market = 'KR' }) {
  const [activeInterval, setActiveInterval] = useState('1d')
  const [activePeriod,   setActivePeriod]   = useState('3mo')

  const { result, loading, load } = useAdvisoryOhlcv()
  const debounceRef = useRef(null)

  // symbol / interval / period 변경 시 API 호출 (symbol 변경은 500ms debounce)
  useEffect(() => {
    if (!symbol) return
    clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => {
      load(symbol, market, activeInterval, activePeriod)
    }, 500)
    return () => clearTimeout(debounceRef.current)
  }, [symbol, market, activeInterval, activePeriod]) // eslint-disable-line

  const handleIntervalChange = (newInterval) => {
    setActiveInterval(newInterval)
    setActivePeriod(DEFAULT_PERIOD[newInterval])
  }

  const ohlcv      = result?.ohlcv      || []
  const indicators = result?.indicators || {}

  if (!symbol) return null

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4 space-y-3">
      {/* 헤더 + 타임프레임 선택 */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <span className="text-xs font-semibold text-gray-700">가격 차트</span>
        <div className="flex items-center gap-2 flex-wrap">
          {/* interval 선택 */}
          <div className="flex rounded border border-gray-200 overflow-hidden text-xs">
            {INTERVAL_OPTS.map(opt => (
              <button
                key={opt.id}
                onClick={() => handleIntervalChange(opt.id)}
                className={`px-2.5 py-1 font-medium transition-colors ${
                  activeInterval === opt.id
                    ? 'bg-indigo-600 text-white'
                    : 'bg-white text-gray-600 hover:bg-gray-50'
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>

          {/* period 선택 */}
          <div className="flex rounded border border-gray-200 overflow-hidden text-xs">
            {(PERIOD_OPTIONS[activeInterval] || []).map(opt => (
              <button
                key={opt.id}
                onClick={() => setActivePeriod(opt.id)}
                className={`px-2.5 py-1 font-medium transition-colors ${
                  activePeriod === opt.id
                    ? 'bg-gray-700 text-white'
                    : 'bg-white text-gray-600 hover:bg-gray-50'
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>

          {loading && (
            <div className="flex items-center gap-1 text-xs text-gray-400">
              <div className="w-3 h-3 border-2 border-indigo-400 border-t-transparent rounded-full animate-spin" />
              로딩 중...
            </div>
          )}
        </div>
      </div>

      {/* 데이터 없음 */}
      {!loading && ohlcv.length === 0 && (
        <div className="text-center py-8 text-gray-400 text-xs">
          차트 데이터가 없습니다
        </div>
      )}

      {/* 캔들스틱 + MA + BB + 거래량 */}
      <CandlestickChart
        ohlcv={ohlcv}
        indicators={indicators}
        interval={activeInterval}
        height={240}
        volumeHeight={55}
        xTickDivisor={6}
      />
    </div>
  )
}
