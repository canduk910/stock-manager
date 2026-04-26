import { useState, useEffect, useRef, useCallback } from 'react'
import { init, dispose } from 'klinecharts'
import { useAdvisoryOhlcv } from '../../hooks/useAdvisory'
import { INTERVAL_OPTS, PERIOD_OPTIONS } from '../common/CandlestickChart'
import { krStyleOverrides } from './klineTheme'

const DEFAULT_PERIOD = { '15m': '60d', '60m': '6mo', '1d': '1y', '1wk': '3y' }

const INDICATORS = [
  { id: 'MA',   label: 'MA',   pane: 'main' },
  { id: 'BOLL', label: 'BB',   pane: 'main' },
  { id: 'VOL',  label: 'VOL',  pane: 'sub' },
  { id: 'MACD', label: 'MACD', pane: 'sub' },
  { id: 'RSI',  label: 'RSI',  pane: 'sub' },
]

function convertToKlineData(ohlcv) {
  return ohlcv.map(d => ({
    timestamp: new Date(d.time).getTime(),
    open: d.open,
    high: d.high,
    low: d.low,
    close: d.close,
    volume: d.volume ?? 0,
  }))
}

export default function KLineChartPanel({ symbol, market }) {
  const [activeInterval, setActiveInterval] = useState('1d')
  const [activePeriod, setActivePeriod] = useState('1y')
  const [activeIndicators, setActiveIndicators] = useState(['MA', 'VOL'])

  const chartContainerRef = useRef(null)
  const chartRef = useRef(null)
  const indicatorPaneIds = useRef({})

  const { result, loading, load } = useAdvisoryOhlcv()

  // API 호출
  useEffect(() => {
    if (symbol && market) {
      load(symbol, market, activeInterval, activePeriod)
    }
  }, [symbol, market, activeInterval, activePeriod, load])

  // 지표 동기화 함수
  const syncIndicators = useCallback((chart, indicators) => {
    // 메인 pane 지표 (MA, BOLL)
    for (const opt of INDICATORS.filter(o => o.pane === 'main')) {
      if (indicators.includes(opt.id)) {
        const config = opt.id === 'MA'
          ? { name: 'MA', calcParams: [5, 20, 60] }
          : opt.id
        chart.createIndicator(config, false, { id: 'candle_pane' })
      } else {
        chart.removeIndicator('candle_pane', opt.id)
      }
    }
    // 하위 pane 지표 (VOL, MACD, RSI)
    for (const opt of INDICATORS.filter(o => o.pane === 'sub')) {
      const existing = indicatorPaneIds.current[opt.id]
      if (indicators.includes(opt.id) && !existing) {
        const paneId = chart.createIndicator(opt.id)
        if (paneId) indicatorPaneIds.current[opt.id] = paneId
      } else if (!indicators.includes(opt.id) && existing) {
        chart.removeIndicator(existing, opt.id)
        delete indicatorPaneIds.current[opt.id]
      }
    }
  }, [])

  // 차트 초기화 + 기본 지표
  useEffect(() => {
    if (!chartContainerRef.current) return
    const chart = init(chartContainerRef.current, {
      styles: krStyleOverrides,
      timezone: 'Asia/Seoul',
    })
    chartRef.current = chart
    syncIndicators(chart, activeIndicators)

    return () => {
      if (chartContainerRef.current) dispose(chartContainerRef.current)
      chartRef.current = null
      indicatorPaneIds.current = {}
    }
  }, []) // eslint-disable-line

  // 데이터 적용
  useEffect(() => {
    if (!chartRef.current || !result?.ohlcv?.length) return
    chartRef.current.applyNewData(convertToKlineData(result.ohlcv))
  }, [result])

  // activeIndicators 변경 시 동기화
  useEffect(() => {
    if (chartRef.current) syncIndicators(chartRef.current, activeIndicators)
  }, [activeIndicators, syncIndicators])

  // resize 처리
  useEffect(() => {
    const handleResize = () => chartRef.current?.resize()
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  const handleIntervalChange = (newInterval) => {
    setActiveInterval(newInterval)
    setActivePeriod(DEFAULT_PERIOD[newInterval])
  }

  const toggleIndicator = (id) => {
    setActiveIndicators(prev =>
      prev.includes(id) ? prev.filter(n => n !== id) : [...prev, id]
    )
  }

  const periodOptions = PERIOD_OPTIONS[activeInterval] || []

  return (
    <div className="bg-white rounded-xl border border-gray-200 px-4 py-4">
      {/* 컨트롤 바 */}
      <div className="flex items-center gap-3 flex-wrap mb-3">
        {/* 타임프레임 */}
        <div className="flex rounded border border-gray-200 overflow-hidden text-xs">
          {INTERVAL_OPTS.map(opt => (
            <button
              key={opt.id}
              onClick={() => handleIntervalChange(opt.id)}
              className={`px-3 py-1.5 font-medium transition-colors ${
                activeInterval === opt.id
                  ? 'bg-indigo-600 text-white'
                  : 'bg-white text-gray-600 hover:bg-gray-50'
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>

        {/* 기간 */}
        <div className="flex rounded border border-gray-200 overflow-hidden text-xs">
          {periodOptions.map(opt => (
            <button
              key={opt.id}
              onClick={() => setActivePeriod(opt.id)}
              className={`px-2.5 py-1.5 font-medium transition-colors ${
                activePeriod === opt.id
                  ? 'bg-gray-700 text-white'
                  : 'bg-white text-gray-500 hover:bg-gray-50'
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>

        {/* 지표 토글 */}
        <div className="flex gap-1 text-xs ml-auto">
          {INDICATORS.map(ind => (
            <button
              key={ind.id}
              onClick={() => toggleIndicator(ind.id)}
              className={`px-2 py-1 rounded border transition-colors ${
                activeIndicators.includes(ind.id)
                  ? 'bg-gray-700 text-white border-gray-700'
                  : 'bg-white text-gray-400 border-gray-200 hover:bg-gray-50'
              }`}
            >
              {ind.label}
            </button>
          ))}
        </div>
      </div>

      {/* 차트 영역 */}
      <div className="relative">
        <div
          ref={chartContainerRef}
          style={{ height: '420px' }}
          className="w-full"
        />
        {loading && (
          <div className="absolute inset-0 flex items-center justify-center bg-white/70">
            <div className="flex items-center gap-2 text-gray-500">
              <div className="w-5 h-5 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
              <span className="text-sm">차트 로딩 중...</span>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
